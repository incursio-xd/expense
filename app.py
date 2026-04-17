from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import hashlib
from datetime import datetime, date
import json

app = Flask(__name__)
app.secret_key = 'expense_tracker_secret_key'

DB_PATH = 'expense_tracker.db'

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS expenses (
        expense_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        amount REAL NOT NULL,
        category TEXT NOT NULL,
        description TEXT,
        date TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(user_id)
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS budgets (
        budget_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        monthly_limit REAL NOT NULL,
        month TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(user_id)
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS goals (
        goal_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        goal_type TEXT NOT NULL,
        target_amount REAL NOT NULL,
        saved_amount REAL DEFAULT 0,
        deadline TEXT NOT NULL,
        description TEXT,
        FOREIGN KEY(user_id) REFERENCES users(user_id)
    )''')
    conn.commit()
    conn.close()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        conn = get_db()
        try:
            conn.execute('INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)',
                         (name, email, hash_password(password)))
            conn.commit()
            flash('Registration successful. Please login.')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Email already registered.')
        finally:
            conn.close()
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        conn = get_db()
        user = conn.execute('SELECT * FROM users WHERE email=? AND password_hash=?',
                            (email, hash_password(password))).fetchone()
        conn.close()
        if user:
            session['user_id'] = user['user_id']
            session['user_name'] = user['name']
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password.')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    user_id = session['user_id']
    conn = get_db()
    today = date.today()
    current_month = today.strftime('%Y-%m')

    # Total expenses this month
    monthly_expenses = conn.execute(
        "SELECT SUM(amount) as total FROM expenses WHERE user_id=? AND date LIKE ?",
        (user_id, current_month + '%')).fetchone()['total'] or 0

    # Budget this month
    budget = conn.execute(
        "SELECT monthly_limit FROM budgets WHERE user_id=? AND month=?",
        (user_id, current_month)).fetchone()
    monthly_limit = budget['monthly_limit'] if budget else 0
    remaining = monthly_limit - monthly_expenses if monthly_limit else 0

    # Today's expenses
    today_expenses = conn.execute(
        "SELECT SUM(amount) as total FROM expenses WHERE user_id=? AND date=?",
        (user_id, str(today))).fetchone()['total'] or 0

    # Category breakdown this month
    categories = conn.execute(
        "SELECT category, SUM(amount) as total FROM expenses WHERE user_id=? AND date LIKE ? GROUP BY category",
        (user_id, current_month + '%')).fetchall()

    # Recent 5 expenses
    recent = conn.execute(
        "SELECT * FROM expenses WHERE user_id=? ORDER BY date DESC LIMIT 5",
        (user_id,)).fetchall()

    # Monthly trend (last 6 months)
    monthly_trend = conn.execute(
        "SELECT strftime('%Y-%m', date) as month, SUM(amount) as total FROM expenses WHERE user_id=? GROUP BY month ORDER BY month DESC LIMIT 6",
        (user_id,)).fetchall()

    conn.close()

    cat_labels = [r['category'] for r in categories]
    cat_values = [r['total'] for r in categories]
    trend_labels = [r['month'] for r in reversed(monthly_trend)]
    trend_values = [r['total'] for r in reversed(monthly_trend)]

    budget_exceeded = monthly_limit > 0 and monthly_expenses > monthly_limit

    return render_template('dashboard.html',
        monthly_expenses=monthly_expenses,
        monthly_limit=monthly_limit,
        remaining=remaining,
        today_expenses=today_expenses,
        recent=recent,
        cat_labels=json.dumps(cat_labels),
        cat_values=json.dumps(cat_values),
        trend_labels=json.dumps(trend_labels),
        trend_values=json.dumps(trend_values),
        budget_exceeded=budget_exceeded,
        current_month=current_month
    )

@app.route('/expenses')
@login_required
def expenses():
    user_id = session['user_id']
    conn = get_db()
    all_expenses = conn.execute(
        "SELECT * FROM expenses WHERE user_id=? ORDER BY date DESC",
        (user_id,)).fetchall()
    conn.close()
    return render_template('expenses.html', expenses=all_expenses)

@app.route('/expenses/add', methods=['GET', 'POST'])
@login_required
def add_expense():
    if request.method == 'POST':
        user_id = session['user_id']
        amount = float(request.form['amount'])
        category = request.form['category']
        description = request.form['description']
        exp_date = request.form['date']
        conn = get_db()
        conn.execute(
            "INSERT INTO expenses (user_id, amount, category, description, date) VALUES (?, ?, ?, ?, ?)",
            (user_id, amount, category, description, exp_date))
        conn.commit()
        conn.close()
        flash('Expense added.')
        return redirect(url_for('expenses'))
    return render_template('add_expense.html', today=str(date.today()))

@app.route('/expenses/edit/<int:expense_id>', methods=['GET', 'POST'])
@login_required
def edit_expense(expense_id):
    user_id = session['user_id']
    conn = get_db()
    expense = conn.execute(
        "SELECT * FROM expenses WHERE expense_id=? AND user_id=?",
        (expense_id, user_id)).fetchone()
    if not expense:
        conn.close()
        flash('Expense not found.')
        return redirect(url_for('expenses'))
    if request.method == 'POST':
        amount = float(request.form['amount'])
        category = request.form['category']
        description = request.form['description']
        exp_date = request.form['date']
        conn.execute(
            "UPDATE expenses SET amount=?, category=?, description=?, date=? WHERE expense_id=?",
            (amount, category, description, exp_date, expense_id))
        conn.commit()
        conn.close()
        flash('Expense updated.')
        return redirect(url_for('expenses'))
    conn.close()
    return render_template('edit_expense.html', expense=expense)

@app.route('/expenses/delete/<int:expense_id>')
@login_required
def delete_expense(expense_id):
    user_id = session['user_id']
    conn = get_db()
    conn.execute("DELETE FROM expenses WHERE expense_id=? AND user_id=?", (expense_id, user_id))
    conn.commit()
    conn.close()
    flash('Expense deleted.')
    return redirect(url_for('expenses'))

@app.route('/budget', methods=['GET', 'POST'])
@login_required
def budget():
    user_id = session['user_id']
    conn = get_db()
    current_month = date.today().strftime('%Y-%m')

    if request.method == 'POST':
        monthly_limit = float(request.form['monthly_limit'])
        month = request.form['month']
        existing = conn.execute(
            "SELECT * FROM budgets WHERE user_id=? AND month=?",
            (user_id, month)).fetchone()
        if existing:
            conn.execute(
                "UPDATE budgets SET monthly_limit=? WHERE user_id=? AND month=?",
                (monthly_limit, user_id, month))
        else:
            conn.execute(
                "INSERT INTO budgets (user_id, monthly_limit, month) VALUES (?, ?, ?)",
                (user_id, monthly_limit, month))
        conn.commit()
        flash('Budget set.')

    all_budgets = conn.execute(
        "SELECT b.*, (SELECT SUM(amount) FROM expenses WHERE user_id=b.user_id AND date LIKE b.month || '%') as spent FROM budgets b WHERE b.user_id=? ORDER BY b.month DESC",
        (user_id,)).fetchall()
    conn.close()
    return render_template('budget.html', budgets=all_budgets, current_month=current_month)

@app.route('/goals')
@login_required
def goals():
    user_id = session['user_id']
    conn = get_db()
    all_goals = conn.execute(
        "SELECT * FROM goals WHERE user_id=? ORDER BY deadline ASC",
        (user_id,)).fetchall()
    conn.close()
    return render_template('goals.html', goals=all_goals)

@app.route('/goals/add', methods=['GET', 'POST'])
@login_required
def add_goal():
    if request.method == 'POST':
        user_id = session['user_id']
        goal_type = request.form['goal_type']
        target_amount = float(request.form['target_amount'])
        saved_amount = float(request.form.get('saved_amount', 0))
        deadline = request.form['deadline']
        description = request.form['description']
        conn = get_db()
        conn.execute(
            "INSERT INTO goals (user_id, goal_type, target_amount, saved_amount, deadline, description) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, goal_type, target_amount, saved_amount, deadline, description))
        conn.commit()
        conn.close()
        flash('Goal added.')
        return redirect(url_for('goals'))
    return render_template('add_goal.html')

@app.route('/goals/update/<int:goal_id>', methods=['GET', 'POST'])
@login_required
def update_goal(goal_id):
    user_id = session['user_id']
    conn = get_db()
    goal = conn.execute(
        "SELECT * FROM goals WHERE goal_id=? AND user_id=?",
        (goal_id, user_id)).fetchone()
    if not goal:
        conn.close()
        flash('Goal not found.')
        return redirect(url_for('goals'))
    if request.method == 'POST':
        saved_amount = float(request.form['saved_amount'])
        conn.execute(
            "UPDATE goals SET saved_amount=? WHERE goal_id=?",
            (saved_amount, goal_id))
        conn.commit()
        conn.close()
        flash('Goal updated.')
        return redirect(url_for('goals'))
    conn.close()
    return render_template('update_goal.html', goal=goal)

@app.route('/goals/delete/<int:goal_id>')
@login_required
def delete_goal(goal_id):
    user_id = session['user_id']
    conn = get_db()
    conn.execute("DELETE FROM goals WHERE goal_id=? AND user_id=?", (goal_id, user_id))
    conn.commit()
    conn.close()
    flash('Goal deleted.')
    return redirect(url_for('goals'))

@app.route('/reports')
@login_required
def reports():
    user_id = session['user_id']
    conn = get_db()
    today = str(date.today())
    current_month = date.today().strftime('%Y-%m')

    # Daily report
    daily = conn.execute(
        "SELECT category, SUM(amount) as total FROM expenses WHERE user_id=? AND date=? GROUP BY category",
        (user_id, today)).fetchall()
    daily_total = conn.execute(
        "SELECT SUM(amount) as total FROM expenses WHERE user_id=? AND date=?",
        (user_id, today)).fetchone()['total'] or 0

    # Monthly report
    monthly = conn.execute(
        "SELECT category, SUM(amount) as total FROM expenses WHERE user_id=? AND date LIKE ? GROUP BY category",
        (user_id, current_month + '%')).fetchall()
    monthly_total = conn.execute(
        "SELECT SUM(amount) as total FROM expenses WHERE user_id=? AND date LIKE ?",
        (user_id, current_month + '%')).fetchone()['total'] or 0

    # Monthly comparison (last 6 months)
    comparison = conn.execute(
        "SELECT strftime('%Y-%m', date) as month, SUM(amount) as total FROM expenses WHERE user_id=? GROUP BY month ORDER BY month DESC LIMIT 6",
        (user_id,)).fetchall()

    conn.close()

    daily_labels = json.dumps([r['category'] for r in daily])
    daily_values = json.dumps([r['total'] for r in daily])
    monthly_labels = json.dumps([r['category'] for r in monthly])
    monthly_values = json.dumps([r['total'] for r in monthly])
    comp_labels = json.dumps([r['month'] for r in reversed(list(comparison))])
    comp_values = json.dumps([r['total'] for r in reversed(list(comparison))])

    return render_template('reports.html',
        today=today,
        current_month=current_month,
        daily_total=daily_total,
        monthly_total=monthly_total,
        daily_labels=daily_labels,
        daily_values=daily_values,
        monthly_labels=monthly_labels,
        monthly_values=monthly_values,
        comp_labels=comp_labels,
        comp_values=comp_values
    )

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
