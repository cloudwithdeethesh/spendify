import re

from database.queries import (
    get_category_breakdown,
    get_recent_transactions,
    get_summary_stats,
    get_user_by_id,
)


class TestGetUserById:
    def test_returns_seed_user(self, seed_user_id):
        user = get_user_by_id(seed_user_id)
        assert user is not None
        assert user["name"] == "Demo User"
        assert user["email"] == "demo@spendly.com"
        assert re.match(r"^[A-Z][a-z]+ \d{4}$", user["member_since"])

    def test_returns_none_for_nonexistent_user(self):
        assert get_user_by_id(99999) is None


class TestGetSummaryStats:
    def test_returns_expected_totals_for_seed_user(self, seed_user_id):
        stats = get_summary_stats(seed_user_id)
        assert stats["total_spent"] == 5440.00
        assert stats["transaction_count"] == 8
        assert stats["top_category"] == "Shopping"

    def test_empty_user_returns_zeros_and_em_dash(self, empty_user_id):
        stats = get_summary_stats(empty_user_id)
        assert stats == {
            "total_spent": 0,
            "transaction_count": 0,
            "top_category": "—",
        }


class TestGetRecentTransactions:
    REQUIRED_KEYS = {"date", "description", "category", "amount"}

    def test_returns_all_seed_rows_newest_first(self, seed_user_id):
        rows = get_recent_transactions(seed_user_id, limit=None)
        assert len(rows) == 8
        assert rows[0]["date"] == "2026-08-20"
        assert rows[-1]["date"] == "2026-08-02"

    def test_each_row_has_required_keys(self, seed_user_id):
        rows = get_recent_transactions(seed_user_id, limit=None)
        assert rows
        for row in rows:
            assert set(row.keys()) == self.REQUIRED_KEYS

    def test_respects_limit(self, seed_user_id):
        rows = get_recent_transactions(seed_user_id, limit=3)
        assert len(rows) == 3
        assert rows[0]["date"] == "2026-08-20"

    def test_limit_none_returns_all(self, seed_user_id):
        rows = get_recent_transactions(seed_user_id, limit=None)
        assert len(rows) == 8

    def test_empty_user_returns_empty_list(self, empty_user_id):
        assert get_recent_transactions(empty_user_id, limit=None) == []


class TestGetCategoryBreakdown:
    def test_returns_all_seven_categories_desc(self, seed_user_id):
        result = get_category_breakdown(seed_user_id)
        assert len(result) == 7
        assert result[0]["name"] == "Shopping"
        assert result[0]["amount"] == 2200.00

    def test_percentages_sum_to_100(self, seed_user_id):
        result = get_category_breakdown(seed_user_id)
        assert sum(row["pct"] for row in result) == 100

    def test_each_row_has_required_keys(self, seed_user_id):
        result = get_category_breakdown(seed_user_id)
        required = {"name", "amount", "pct"}
        for row in result:
            assert required.issubset(row.keys())

    def test_empty_user_returns_empty_list(self, empty_user_id):
        assert get_category_breakdown(empty_user_id) == []


class TestProfileRoute:
    def test_unauthenticated_redirects_to_login(self, app):
        with app.test_client() as c:
            response = c.get("/profile")
            assert response.status_code == 302
            assert "/login" in response.headers.get("Location", "")

    def test_stale_session_redirects_to_login(self, app):
        with app.test_client() as c:
            with c.session_transaction() as sess:
                sess["user_id"] = 999999
                sess["user_name"] = "Ghost"
            response = c.get("/profile")
            assert response.status_code == 302
            assert "/login" in response.headers.get("Location", "")

    def test_authenticated_seed_user_response(self, client):
        response = client.get("/profile")
        assert response.status_code == 200

        body = response.get_data(as_text=True)

        assert "Demo User" in body
        assert "demo@spendly.com" in body
        assert "₹5,440.00" in body
        assert "Shopping" in body
        assert "Member since " in body

        newest_first = [
            "Groceries",
            "Miscellaneous",
            "New shoes",
            "Movie ticket",
            "Pharmacy",
            "Electricity bill",
            "Metro card recharge",
            "Lunch at cafe",
        ]
        for description in newest_first:
            assert description in body
        positions = [body.index(desc) for desc in newest_first]
        assert positions == sorted(positions), (
            "transactions should render newest-first in the profile HTML"
        )

        for name in (
            "Food",
            "Transport",
            "Bills",
            "Health",
            "Entertainment",
            "Shopping",
            "Other",
        ):
            assert name in body
        assert "category-row-fill--shopping" in body

    def test_empty_user_profile_renders(self, app, empty_user_id):
        with app.test_client() as c:
            with c.session_transaction() as sess:
                sess["user_id"] = empty_user_id
                sess["user_name"] = "Empty User"
            response = c.get("/profile")
            assert response.status_code == 200
            body = response.get_data(as_text=True)
            assert "Empty User" in body
            assert "₹0.00" in body
            assert "—" in body
