import os
import sqlite3
from datetime import date

from flask import Flask, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash

from database.db import create_user, get_db, get_user_by_email, init_db, seed_db
from database.queries import (
    CATEGORY_SLUGS,
    get_category_breakdown,
    get_recent_transactions,
    get_summary_stats,
    get_user_by_id,
)
from filters import resolve_range

app = Flask(__name__)


def _initials_from_name(name):
    if not name or not name.strip():
        return "?"
    parts = name.split()
    if len(parts) == 1:
        return parts[0][0].upper()
    return (parts[0][0] + parts[-1][0]).upper()
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

    user_id = session["user_id"]

    user = get_user_by_id(user_id)
    if user is None:
        session.clear()
        return redirect(url_for("login"))
    user["initials"] = _initials_from_name(user["name"])

    resolved = resolve_range(
        request.args.get("range"),
        request.args.get("from"),
        request.args.get("to"),
        date.today(),
    )
    date_range = (
        None
        if resolved["active_range"] == "all"
        else (resolved["from_date"], resolved["to_date"])
    )

    stats = get_summary_stats(user_id, date_range=date_range)

    transactions = [
        {**tx, "category_slug": CATEGORY_SLUGS.get(tx["category"], "other")}
        for tx in get_recent_transactions(user_id, limit=None, date_range=date_range)
    ]

    category_breakdown = [
        {
            "name": row["name"],
            "slug": CATEGORY_SLUGS.get(row["name"], "other"),
            "total": row["amount"],
            "percent": row["pct"],
        }
        for row in get_category_breakdown(user_id, date_range=date_range)
    ]

    return render_template(
        "profile.html",
        user=user,
        stats=stats,
        transactions=transactions,
        category_breakdown=category_breakdown,
        active_range=resolved["active_range"],
        range_label=resolved["label"],
        range_error=resolved["error"],
        from_date=resolved["from_date"],
        to_date=resolved["to_date"],
    )


@app.route("/analytics")
def analytics():
    if not session.get("user_id"):
        return redirect(url_for("login"))
    return render_template("analytics.html")


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
