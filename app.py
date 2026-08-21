import os
import sqlite3

from flask import Flask, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash

from database.db import create_user, get_db, get_user_by_email, init_db, seed_db

app = Flask(__name__)
# TODO: override in production via the SPENDLY_SECRET_KEY environment variable.
app.secret_key = os.environ.get(
    "SPENDLY_SECRET_KEY", "dev-only-not-for-production-change-me"
)


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if session.get("user_id"):
        return redirect(url_for("landing"))

    if request.method == "GET":
        return render_template("register.html")

    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    password = request.form.get("password", "")
    confirm_password = request.form.get("confirm_password", "")

    if not name or not email or not password or not confirm_password:
        return render_template(
            "register.html",
            error="All fields are required.",
            name=name,
            email=email,
        )

    if len(password) < 8:
        return render_template(
            "register.html",
            error="Password must be at least 8 characters.",
            name=name,
            email=email,
        )

    if password != confirm_password:
        return render_template(
            "register.html",
            error="Passwords do not match.",
            name=name,
            email=email,
        )

    try:
        create_user(name, email, password)
    except sqlite3.IntegrityError:
        return render_template(
            "register.html",
            error="An account with that email already exists.",
            name=name,
            email=email,
        )

    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("landing"))

    if request.method == "GET":
        return render_template("login.html")

    email = request.form.get("email", "").strip()
    password = request.form.get("password", "")

    if not email or not password:
        return render_template(
            "login.html",
            error="Invalid email or password.",
            email=email,
        )

    user = get_user_by_email(email)
    if user is None or not check_password_hash(user["password_hash"], password):
        return render_template(
            "login.html",
            error="Invalid email or password.",
            email=email,
        )

    session["user_id"] = user["id"]
    session["user_name"] = user["name"]
    return redirect(url_for("profile"))


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("landing"))


@app.route("/profile")
def profile():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    user = {
        "name": session.get("user_name", "Demo User"),
        "email": "demo@spendly.com",
        "initials": "DU",
        "member_since": "August 2026",
    }
    stats = {
        "total_spent": 5440.00,
        "transaction_count": 8,
        "top_category": "Shopping",
    }
    transactions = [
        {"date": "2026-08-20", "description": "Groceries",           "category": "Food",          "category_slug": "food",          "amount": 180.00},
        {"date": "2026-08-19", "description": "Miscellaneous",       "category": "Other",         "category_slug": "other",         "amount": 90.00},
        {"date": "2026-08-17", "description": "New shoes",           "category": "Shopping",      "category_slug": "shopping",      "amount": 2200.00},
        {"date": "2026-08-14", "description": "Movie ticket",        "category": "Entertainment", "category_slug": "entertainment", "amount": 350.00},
        {"date": "2026-08-10", "description": "Pharmacy",            "category": "Health",        "category_slug": "health",        "amount": 450.00},
        {"date": "2026-08-07", "description": "Electricity bill",    "category": "Bills",         "category_slug": "bills",         "amount": 1800.00},
        {"date": "2026-08-05", "description": "Metro card recharge", "category": "Transport",     "category_slug": "transport",     "amount": 120.00},
        {"date": "2026-08-02", "description": "Lunch at cafe",       "category": "Food",          "category_slug": "food",          "amount": 250.00},
    ]
    category_breakdown = [
        {"name": "Shopping",      "slug": "shopping",      "total": 2200.00, "percent": 40},
        {"name": "Bills",         "slug": "bills",         "total": 1800.00, "percent": 33},
        {"name": "Health",        "slug": "health",        "total": 450.00,  "percent": 8},
        {"name": "Food",          "slug": "food",          "total": 430.00,  "percent": 8},
        {"name": "Entertainment", "slug": "entertainment", "total": 350.00,  "percent": 6},
        {"name": "Transport",     "slug": "transport",     "total": 120.00,  "percent": 2},
        {"name": "Other",         "slug": "other",         "total": 90.00,   "percent": 2},
    ]
    return render_template(
        "profile.html",
        user=user,
        stats=stats,
        transactions=transactions,
        category_breakdown=category_breakdown,
    )


@app.route("/expenses/add")
def add_expense():
    return "Add expense — coming in Step 7"


@app.route("/expenses/<int:id>/edit")
def edit_expense(id):
    return "Edit expense — coming in Step 8"


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return "Delete expense — coming in Step 9"


with app.app_context():
    init_db()
    seed_db()


if __name__ == "__main__":
    app.run(debug=True, port=5001)
