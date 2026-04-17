# Smart Expense Tracker

A personal finance web application built with Flask and SQLite. Track daily expenses, set monthly budgets, manage savings goals, and view spending reports with interactive charts.

---

## Features

- **User Authentication** — Register and log in with hashed passwords
- **Expense Management** — Add, edit, and delete expenses with category tagging
- **Budget Tracking** — Set monthly spending limits and monitor budget usage
- **Savings Goals** — Create financial goals and track progress toward them
- **Reports & Charts** — Visual daily, monthly, and trend breakdowns using Chart.js
- **Dashboard** — At-a-glance overview of today's spending, monthly totals, and recent activity

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3, Flask |
| Database | SQLite |
| Frontend | Jinja2 templates, HTML, CSS |
| Charts | Chart.js (CDN) |

---

## Project Structure

```
expense-tracker/
├── app.py                  # Main Flask application
├── expense_tracker.db      # SQLite database (auto-created on first run)
└── templates/
    ├── base.html           # Shared layout and navigation
    ├── login.html          # Login page
    ├── register.html       # Registration page
    ├── dashboard.html      # Main dashboard with charts
    ├── expenses.html       # Expense list
    ├── add_expense.html    # Add expense form
    ├── edit_expense.html   # Edit expense form
    ├── budget.html         # Budget management
    ├── goals.html          # Goals list
    ├── add_goal.html       # Add goal form
    ├── update_goal.html    # Update goal progress
    └── reports.html        # Reports and analytics
```

---

## Getting Started

### Prerequisites

- Python 3.7+
- pip

### Installation

1. Clone or download the project:
   ```bash
   git clone <repository-url>
   cd expense-tracker
   ```

2. Install dependencies:
   ```bash
   pip install flask
   ```

3. Run the app:
   ```bash
   python app.py
   ```

4. Open your browser and navigate to:
   ```
   http://127.0.0.1:5000
   ```

The SQLite database (`expense_tracker.db`) is created automatically on first run.

---

## Usage

1. **Register** a new account at `/register`
2. **Log in** with your email and password
3. **Add expenses** from the dashboard or the Expenses page
4. **Set a budget** under the Budget tab for the current month
5. **Create goals** (e.g. saving for a vacation) and update progress over time
6. **View reports** for daily and monthly breakdowns and a 6-month spending comparison

---

## Expense Categories

Food, Housing, Transportation, Healthcare, Education, Entertainment, Shopping, Other

---

## Database Schema

**users** — `user_id`, `name`, `email`, `password_hash`

**expenses** — `expense_id`, `user_id`, `amount`, `category`, `description`, `date`

**budgets** — `budget_id`, `user_id`, `monthly_limit`, `month`

**goals** — `goal_id`, `user_id`, `goal_type`, `target_amount`, `saved_amount`, `deadline`, `description`

---

## Security Notes

- Passwords are hashed using SHA-256 before storage
- All routes that require authentication are protected with a `login_required` decorator
- Session data is managed server-side via Flask's session mechanism
- For production use, replace the `secret_key` in `app.py` with a strong, randomly generated value and consider upgrading to bcrypt for password hashing

---

## License

This project is for personal/educational use.
