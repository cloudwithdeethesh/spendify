from datetime import datetime

from database.db import get_db

CATEGORY_SLUGS = {
    "Food": "food",
    "Transport": "transport",
    "Bills": "bills",
    "Health": "health",
    "Entertainment": "entertainment",
    "Shopping": "shopping",
    "Other": "other",
}


def get_user_by_id(user_id):
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT name, email, created_at FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
        if row is None:
            return None
        created_at = row["created_at"]
        try:
            member_since = datetime.strptime(
                created_at, "%Y-%m-%d %H:%M:%S"
            ).strftime("%B %Y")
        except (ValueError, TypeError):
            member_since = created_at
        return {
            "name": row["name"],
            "email": row["email"],
            "member_since": member_since,
        }
    finally:
        conn.close()


def get_summary_stats(user_id):
    conn = get_db()
    try:
        total, count = conn.execute(
            "SELECT COALESCE(SUM(amount), 0), COUNT(*) FROM expenses WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        if count == 0:
            return {"total_spent": 0, "transaction_count": 0, "top_category": "—"}
        top_row = conn.execute(
            "SELECT category FROM expenses WHERE user_id = ? "
            "GROUP BY category ORDER BY SUM(amount) DESC LIMIT 1",
            (user_id,),
        ).fetchone()
        top_category = top_row["category"] if top_row else "—"
        return {
            "total_spent": float(total),
            "transaction_count": int(count),
            "top_category": top_category,
        }
    finally:
        conn.close()


def get_recent_transactions(user_id, limit=10):
    conn = get_db()
    try:
        sql = (
            "SELECT date, description, category, amount "
            "FROM expenses WHERE user_id = ? "
            "ORDER BY date DESC, id DESC"
        )
        params = [user_id]
        if limit is not None:
            sql += " LIMIT ?"
            params.append(limit)
        rows = conn.execute(sql, params).fetchall()
        return [
            {
                "date": row["date"],
                "description": row["description"],
                "category": row["category"],
                "amount": row["amount"],
            }
            for row in rows
        ]
    finally:
        conn.close()


def get_category_breakdown(user_id):
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT category AS name, SUM(amount) AS amount "
            "FROM expenses WHERE user_id = ? "
            "GROUP BY category ORDER BY amount DESC",
            (user_id,),
        ).fetchall()
    finally:
        conn.close()

    if not rows:
        return []

    total = sum(row["amount"] for row in rows)
    if total == 0:
        return [
            {"name": row["name"], "amount": row["amount"], "pct": 0}
            for row in rows
        ]

    breakdown = [
        {
            "name": row["name"],
            "amount": row["amount"],
            "pct": round(row["amount"] / total * 100),
        }
        for row in rows
    ]

    # Absorb rounding drift into the largest row so pcts sum to exactly 100.
    breakdown[0]["pct"] += 100 - sum(item["pct"] for item in breakdown)

    return breakdown
