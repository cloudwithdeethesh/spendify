import random
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from database.db import get_db, init_db

CATEGORY_CONFIG = {
    "Food": {
        "weight": 8,
        "min": 50,
        "max": 800,
        "descriptions": [
            "Lunch at cafe", "Groceries", "Chai and snacks", "Zomato order",
            "Swiggy dinner", "Fruits and vegetables", "Roadside chaat",
            "Weekend brunch", "Ice cream treat", "Bakery items",
        ],
    },
    "Transport": {
        "weight": 6,
        "min": 20,
        "max": 500,
        "descriptions": [
            "Auto rickshaw", "Ola ride", "Uber cab", "Metro card recharge",
            "Petrol", "Bus fare", "Parking charges", "Rapido bike",
        ],
    },
    "Bills": {
        "weight": 4,
        "min": 200,
        "max": 3000,
        "descriptions": [
            "Electricity bill", "Water bill", "Broadband recharge",
            "Mobile recharge", "DTH recharge", "Gas cylinder", "Rent share",
        ],
    },
    "Health": {
        "weight": 2,
        "min": 100,
        "max": 2000,
        "descriptions": [
            "Pharmacy", "Doctor consultation", "Blood test", "Gym membership",
            "Yoga class", "Dentist visit",
        ],
    },
    "Entertainment": {
        "weight": 2,
        "min": 100,
        "max": 1500,
        "descriptions": [
            "Movie ticket", "Netflix subscription", "Spotify premium",
            "Concert ticket", "Weekend outing", "Amusement park",
        ],
    },
    "Shopping": {
        "weight": 4,
        "min": 200,
        "max": 5000,
        "descriptions": [
            "Amazon order", "Flipkart purchase", "New shoes", "Clothing",
            "Kitchenware", "Home decor", "Myntra order",
        ],
    },
    "Other": {
        "weight": 3,
        "min": 50,
        "max": 1000,
        "descriptions": [
            "Gift for friend", "Donation", "Miscellaneous", "Stationery",
            "Salon visit", "Repair charges",
        ],
    },
}


def parse_args(argv):
    if len(argv) != 4:
        return None
    try:
        return int(argv[1]), int(argv[2]), int(argv[3])
    except ValueError:
        return None


def print_usage():
    print(
        "Usage: /seed-expenses <user_id> <count> <months>\n"
        "Example: /seed-expenses 1 50 6"
    )


def user_exists(conn, user_id):
    row = conn.execute("SELECT 1 FROM users WHERE id = ?", (user_id,)).fetchone()
    return row is not None


def random_date_within(months):
    today = date.today()
    span_days = max(months * 30, 1)
    delta = random.randint(0, span_days)
    return today - timedelta(days=delta)


def pick_category():
    categories = list(CATEGORY_CONFIG.keys())
    weights = [CATEGORY_CONFIG[c]["weight"] for c in categories]
    return random.choices(categories, weights=weights, k=1)[0]


def build_expense(user_id, months):
    category = pick_category()
    cfg = CATEGORY_CONFIG[category]
    amount = round(random.uniform(cfg["min"], cfg["max"]), 2)
    description = random.choice(cfg["descriptions"])
    d = random_date_within(months).isoformat()
    return (user_id, amount, category, d, description)


def main():
    args = parse_args(sys.argv)
    if args is None:
        print_usage()
        sys.exit(1)

    user_id, count, months = args
    if count <= 0 or months <= 0:
        print_usage()
        sys.exit(1)

    init_db()
    conn = get_db()
    try:
        if not user_exists(conn, user_id):
            print(f"No user found with id {user_id}.")
            sys.exit(1)

        expenses = [build_expense(user_id, months) for _ in range(count)]

        try:
            conn.execute("BEGIN")
            conn.executemany(
                "INSERT INTO expenses (user_id, amount, category, date, description) "
                "VALUES (?, ?, ?, ?, ?)",
                expenses,
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise

        dates = sorted(e[3] for e in expenses)
        print(f"Inserted {len(expenses)} expenses for user_id={user_id}.")
        print(f"Date range: {dates[0]} to {dates[-1]}")
        print("Sample:")
        sample = expenses[:5]
        for user_id_, amount, category, d, description in sample:
            print(f"  {d}  {category:<13} ₹{amount:>8.2f}  {description}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
