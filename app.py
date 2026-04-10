from flask import Flask, render_template, request, redirect, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import date, datetime
from collections import defaultdict

# Import models
from models import db, User, Expense, Budget

app = Flask(__name__)
app.secret_key = "expense-secret"

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///expense.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)


# ================= ROOT =================

@app.route("/")
def home():
    return redirect("/login")


# ================= AUTH =================

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = User.query.filter_by(username=request.form["username"]).first()

        if user and check_password_hash(user.password, request.form["password"]):
            session["user_id"] = user.id
            return redirect("/dashboard")

        flash("Invalid username or password")

    return render_template("login.html")


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":

        if User.query.filter_by(username=request.form["username"]).first():
            flash("Username already exists")
            return redirect("/signup")

        hashed = generate_password_hash(request.form["password"])

        db.session.add(
            User(
                username=request.form["username"],
                password=hashed
            )
        )

        db.session.commit()

        flash("Account created successfully")

        return redirect("/login")

    return render_template("signup.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


# ================= DASHBOARD =================

@app.route("/dashboard")
def dashboard():

    if "user_id" not in session:
        return redirect("/login")

    selected_date_str = request.args.get("date", date.today().isoformat())

    selected_date = datetime.strptime(
        selected_date_str,
        "%Y-%m-%d"
    ).date()

    categories = [
        "Food",
        "Shopping",
        "Transport",
        "Bills",
        "Entertainment",
        "Other"
    ]

    expenses = Expense.query.filter_by(
        user_id=session["user_id"],
        created_on=selected_date
    ).all()

    daily_total = sum(e.amount for e in expenses)

    month_prefix = selected_date.strftime("%Y-%m")

    monthly_total = sum(
        e.amount for e in Expense.query.filter(
            Expense.user_id == session["user_id"],
            Expense.created_on.like(f"{month_prefix}%")
        ).all()
    )

    top_category = "-"

    if expenses:
        temp = defaultdict(float)

        for e in expenses:
            temp[e.category] += e.amount

        top_category = max(temp, key=temp.get)

    return render_template(
        "dashboard.html",
        expenses=expenses,
        categories=categories,
        selected_date=selected_date_str,
        daily_total=daily_total,
        monthly_total=monthly_total,
        top_category=top_category
    )


# ================= ADD EXPENSE =================

@app.route("/add-expense", methods=["POST"])
def add_expense():

    if "user_id" not in session:
        return redirect("/login")

    expense_date = datetime.strptime(
        request.form["date"],
        "%Y-%m-%d"
    ).date()

    expense = Expense(
        amount=float(request.form["amount"]),
        category=request.form["category"].strip().title(),
        description=request.form.get("description", ""),
        created_on=expense_date,
        user_id=session["user_id"]
    )

    db.session.add(expense)
    db.session.commit()

    return redirect("/dashboard")


# ================= EDIT EXPENSE =================

@app.route("/edit/<int:expense_id>", methods=["GET", "POST"])
def edit_expense(expense_id):

    if "user_id" not in session:
        return redirect("/login")

    expense = Expense.query.filter_by(
        id=expense_id,
        user_id=session["user_id"]
    ).first_or_404()

    categories = [
        "Food",
        "Shopping",
        "Transport",
        "Bills",
        "Entertainment",
        "Other"
    ]

    if request.method == "POST":

        expense.amount = float(request.form["amount"])

        expense.category = request.form["category"].strip().title()

        expense.description = request.form.get("description", "")

        expense.created_on = datetime.strptime(
            request.form["date"],
            "%Y-%m-%d"
        ).date()

        db.session.commit()

        return redirect("/dashboard")

    return render_template(
        "edit_expense.html",
        expense=expense,
        categories=categories
    )


# ================= DELETE EXPENSE =================

@app.route("/delete/<int:expense_id>", methods=["POST"])
def delete_expense(expense_id):

    if "user_id" not in session:
        return redirect("/login")

    expense = Expense.query.filter_by(
        id=expense_id,
        user_id=session["user_id"]
    ).first_or_404()

    db.session.delete(expense)
    db.session.commit()

    flash("Expense deleted successfully")

    return redirect("/dashboard")


# ================= ANALYTICS =================

@app.route("/analytics")
def analytics():

    if "user_id" not in session:
        return redirect("/login")

    selected_date_str = request.args.get("date", date.today().isoformat())

    selected_date = datetime.strptime(
        selected_date_str,
        "%Y-%m-%d"
    ).date()

    daily_map = defaultdict(float)

    expenses = Expense.query.filter_by(
        user_id=session["user_id"],
        created_on=selected_date
    ).all()

    for e in expenses:
        daily_map[e.category] += e.amount

    month_prefix = selected_date.strftime("%Y-%m")

    monthly_map = defaultdict(float)

    monthly_expenses = Expense.query.filter(
        Expense.user_id == session["user_id"],
        Expense.created_on.like(f"{month_prefix}%")
    ).all()

    for e in monthly_expenses:
        monthly_map[e.created_on.day] += e.amount

    sorted_days = sorted(monthly_map.keys())

    return render_template(
        "analytics.html",
        selected_date=selected_date_str,
        daily_categories=list(daily_map.keys()),
        daily_amounts=list(daily_map.values()),
        days=sorted_days,
        monthly_amounts=[monthly_map[d] for d in sorted_days]
    )


# ================= SUMMARY =================

@app.route("/summary")
def summary():

    if "user_id" not in session:
        return redirect("/login")

    selected_date_str = request.args.get("date", date.today().isoformat())

    selected_date = datetime.strptime(
        selected_date_str,
        "%Y-%m-%d"
    ).date()

    expenses = Expense.query.filter_by(
        user_id=session["user_id"],
        created_on=selected_date
    ).all()

    daily_total = sum(e.amount for e in expenses)

    month_prefix = selected_date.strftime("%Y-%m")

    monthly_total = sum(
        e.amount for e in Expense.query.filter(
            Expense.user_id == session["user_id"],
            Expense.created_on.like(f"{month_prefix}%")
        ).all()
    )

    top_category = "-"

    if expenses:
        temp = defaultdict(float)

        for e in expenses:
            temp[e.category] += e.amount

        top_category = max(temp, key=temp.get)

    return render_template(
        "summary.html",
        selected_date=selected_date_str,
        daily_total=daily_total,
        monthly_total=monthly_total,
        top_category=top_category
    )


# ================= START =================

if __name__ == "__main__":
    with app.app_context():
        db.create_all()

    app.run(debug=True)
