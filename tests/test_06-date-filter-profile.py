"""
tests/test_06-date-filter-profile.py

Pytest test suite for Step 6: Date Filter for Profile Page.

Tests are derived exclusively from the spec
(.claude/specs/06-date-filter-profile.md) and the Definition of Done
listed there. No implementation details are assumed beyond the public API
described in the spec.
"""

import importlib
from datetime import date, timedelta

import pytest

import database.db as db_module
from app import app as flask_app
from database.db import init_db, seed_db
from database.queries import (
    get_category_breakdown,
    get_recent_transactions,
    get_summary_stats,
)
from filters import resolve_range

# ---------------------------------------------------------------------------
# Constants mirrored from seed data (db.py) — used for assertion values only.
# ---------------------------------------------------------------------------

SEED_EMAIL = "demo@spendly.com"
SEED_PASSWORD = "demo123"

# All 8 seed expenses are in August 2026.
SEED_TOTAL = 5440.00          # 250+120+1800+450+350+2200+90+180
SEED_COUNT = 8
SEED_TOP_CATEGORY = "Shopping"   # highest single-category total: ₹2200

# Expenses with date between 2026-08-01 and 2026-08-10 (inclusive):
#   Food ₹250 (08-02), Transport ₹120 (08-05), Bills ₹1800 (08-07), Health ₹450 (08-10)
RANGE_AUG_1_10 = ("2026-08-01", "2026-08-10")
RANGE_AUG_1_10_TOTAL = 2620.00   # 250+120+1800+450
RANGE_AUG_1_10_COUNT = 4
RANGE_AUG_1_10_TOP = "Bills"     # ₹1800 dominates

# Pinned "today" for deterministic preset calculations.
TODAY = date(2026, 8, 24)

EMPTY_RANGE = ("2020-01-01", "2020-01-31")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session", autouse=True)
def patch_db_path(tmp_path_factory):
    """Redirect all DB operations to a temp file for the whole session."""
    tmp_db = tmp_path_factory.mktemp("data") / "test_spendly.db"
    db_module.DB_PATH = tmp_db
    # Re-import get_db so queries.py picks up the patched path.
    importlib.reload(db_module)
    import database.queries as queries_module  # noqa: F401 — reload ensures it uses new path
    importlib.reload(queries_module)
    init_db()
    seed_db()
    yield


@pytest.fixture
def app():
    flask_app.config.update(
        {
            "TESTING": True,
            "SECRET_KEY": "test-secret-key",
            "WTF_CSRF_ENABLED": False,
        }
    )
    yield flask_app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def logged_in_client(client):
    """Test client with an active session for the seed demo user."""
    response = client.post(
        "/login",
        data={"email": SEED_EMAIL, "password": SEED_PASSWORD},
        follow_redirects=False,
    )
    # A successful login redirects away from /login.
    assert response.status_code in (302, 200), (
        f"Login failed — got {response.status_code}; "
        f"body: {response.data[:300]}"
    )
    return client


# ---------------------------------------------------------------------------
# Helper: fetch the demo user_id from the real DB after seed.
# ---------------------------------------------------------------------------

def _demo_user_id():
    from database.db import get_db
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT id FROM users WHERE email = ?", (SEED_EMAIL,)
        ).fetchone()
        return row["id"]
    finally:
        conn.close()


# ===========================================================================
# 1. resolve_range unit tests
# ===========================================================================

class TestResolveRangePresets:
    """All presets with TODAY = 2026-08-24."""

    def test_this_month_from_date(self):
        """this_month: from_date is the first day of the current month."""
        result = resolve_range("this_month", None, None, TODAY)
        assert result["from_date"] == "2026-08-01", (
            "this_month should start on the 1st of the current month"
        )

    def test_this_month_to_date(self):
        """this_month: to_date is today."""
        result = resolve_range("this_month", None, None, TODAY)
        assert result["to_date"] == "2026-08-24", (
            "this_month should end on today's date"
        )

    def test_this_month_active_range_and_no_error(self):
        """this_month: active_range == 'this_month', error is None."""
        result = resolve_range("this_month", None, None, TODAY)
        assert result["active_range"] == "this_month"
        assert result["error"] is None

    def test_this_month_label_contains_month_name(self):
        """this_month: label contains the human-readable text 'This month'."""
        result = resolve_range("this_month", None, None, TODAY)
        assert "This month" in result["label"], (
            f"Expected 'This month' in label, got: {result['label']}"
        )

    def test_last_month_from_date(self):
        """last_month: from_date is the first day of July 2026."""
        result = resolve_range("last_month", None, None, TODAY)
        assert result["from_date"] == "2026-07-01", (
            "last_month from_date should be July 1 when today is Aug 24"
        )

    def test_last_month_to_date(self):
        """last_month: to_date is the last day of July 2026."""
        result = resolve_range("last_month", None, None, TODAY)
        assert result["to_date"] == "2026-07-31", (
            "last_month to_date should be July 31 when today is Aug 24"
        )

    def test_last_month_active_range_and_no_error(self):
        """last_month: active_range == 'last_month', error is None."""
        result = resolve_range("last_month", None, None, TODAY)
        assert result["active_range"] == "last_month"
        assert result["error"] is None

    def test_last_month_label_contains_last_month(self):
        """last_month: label contains the text 'Last month'."""
        result = resolve_range("last_month", None, None, TODAY)
        assert "Last month" in result["label"], (
            f"Expected 'Last month' in label, got: {result['label']}"
        )

    def test_last_month_wraps_from_january(self):
        """last_month: Jan today → from=Dec 1 previous year, to=Dec 31."""
        jan_today = date(2026, 1, 15)
        result = resolve_range("last_month", None, None, jan_today)
        assert result["from_date"] == "2025-12-01", (
            "last_month from_date should be December 1 2025 when today is Jan 15 2026"
        )
        assert result["to_date"] == "2025-12-31", (
            "last_month to_date should be December 31 2025 when today is Jan 15 2026"
        )

    def test_last_7_days_from_date(self):
        """last_7_days: from_date is today minus 6 days (7 days inclusive)."""
        result = resolve_range("last_7_days", None, None, TODAY)
        expected_from = (TODAY - timedelta(days=6)).isoformat()
        assert result["from_date"] == expected_from, (
            f"last_7_days from_date should be {expected_from}, got {result['from_date']}"
        )

    def test_last_7_days_to_date(self):
        """last_7_days: to_date is today."""
        result = resolve_range("last_7_days", None, None, TODAY)
        assert result["to_date"] == TODAY.isoformat()

    def test_last_7_days_active_range_and_no_error(self):
        """last_7_days: active_range == 'last_7_days', error is None."""
        result = resolve_range("last_7_days", None, None, TODAY)
        assert result["active_range"] == "last_7_days"
        assert result["error"] is None

    def test_last_30_days_from_date(self):
        """last_30_days: from_date is today minus 29 days (30 days inclusive)."""
        result = resolve_range("last_30_days", None, None, TODAY)
        expected_from = (TODAY - timedelta(days=29)).isoformat()
        assert result["from_date"] == expected_from, (
            f"last_30_days from_date should be {expected_from}, got {result['from_date']}"
        )

    def test_last_30_days_to_date(self):
        """last_30_days: to_date is today."""
        result = resolve_range("last_30_days", None, None, TODAY)
        assert result["to_date"] == TODAY.isoformat()

    def test_last_30_days_active_range_and_no_error(self):
        """last_30_days: active_range == 'last_30_days', error is None."""
        result = resolve_range("last_30_days", None, None, TODAY)
        assert result["active_range"] == "last_30_days"
        assert result["error"] is None

    def test_all_active_range_and_no_error(self):
        """all: active_range == 'all', error is None."""
        result = resolve_range("all", None, None, TODAY)
        assert result["active_range"] == "all"
        assert result["error"] is None

    def test_all_label(self):
        """all: label is 'All time' (no date window suffix)."""
        result = resolve_range("all", None, None, TODAY)
        assert "All time" in result["label"], (
            f"Expected 'All time' in label for 'all' range, got: {result['label']}"
        )


class TestResolveRangeCustom:
    """Custom range validation tests."""

    def test_custom_valid_dates_echoed_back(self):
        """custom with valid dates: from_date and to_date are echoed back."""
        result = resolve_range("custom", "2026-08-01", "2026-08-10", TODAY)
        assert result["from_date"] == "2026-08-01"
        assert result["to_date"] == "2026-08-10"

    def test_custom_valid_active_range_is_custom(self):
        """custom with valid dates: active_range == 'custom'."""
        result = resolve_range("custom", "2026-08-01", "2026-08-10", TODAY)
        assert result["active_range"] == "custom"

    def test_custom_valid_no_error(self):
        """custom with valid dates: error is None."""
        result = resolve_range("custom", "2026-08-01", "2026-08-10", TODAY)
        assert result["error"] is None

    def test_custom_valid_label_contains_custom_range(self):
        """custom with valid dates: label contains 'Custom range'."""
        result = resolve_range("custom", "2026-08-01", "2026-08-10", TODAY)
        assert "Custom range" in result["label"], (
            f"Expected 'Custom range' in label, got: {result['label']}"
        )

    def test_custom_missing_from_date_falls_back_to_this_month(self):
        """custom with missing from date: falls back to this_month."""
        result = resolve_range("custom", None, "2026-08-10", TODAY)
        assert result["active_range"] == "this_month", (
            "Missing from date should fall back to this_month"
        )

    def test_custom_missing_from_date_sets_error(self):
        """custom with missing from date: error is not None."""
        result = resolve_range("custom", None, "2026-08-10", TODAY)
        assert result["error"] is not None, (
            "Missing from date must set an error message"
        )

    def test_custom_missing_to_date_falls_back_to_this_month(self):
        """custom with missing to date: falls back to this_month."""
        result = resolve_range("custom", "2026-08-01", None, TODAY)
        assert result["active_range"] == "this_month", (
            "Missing to date should fall back to this_month"
        )

    def test_custom_missing_to_date_sets_error(self):
        """custom with missing to date: error is not None."""
        result = resolve_range("custom", "2026-08-01", None, TODAY)
        assert result["error"] is not None

    def test_custom_both_missing_falls_back_to_this_month(self):
        """custom with both dates missing: falls back to this_month."""
        result = resolve_range("custom", None, None, TODAY)
        assert result["active_range"] == "this_month"
        assert result["error"] is not None

    def test_custom_malformed_from_date_falls_back_to_this_month(self):
        """custom with malformed from date: falls back to this_month."""
        result = resolve_range("custom", "not-a-date", "2026-08-10", TODAY)
        assert result["active_range"] == "this_month", (
            "Malformed from date should fall back to this_month"
        )

    def test_custom_malformed_from_date_sets_error(self):
        """custom with malformed from date: error is not None."""
        result = resolve_range("custom", "not-a-date", "2026-08-10", TODAY)
        assert result["error"] is not None, (
            "Malformed date must produce an error message"
        )

    def test_custom_malformed_to_date_falls_back_to_this_month(self):
        """custom with malformed to date: falls back to this_month."""
        result = resolve_range("custom", "2026-08-01", "2026/08/10", TODAY)
        assert result["active_range"] == "this_month"

    def test_custom_from_greater_than_to_falls_back_to_this_month(self):
        """custom from > to: falls back to this_month."""
        result = resolve_range("custom", "2026-08-10", "2026-08-01", TODAY)
        assert result["active_range"] == "this_month", (
            "from > to should fall back to this_month"
        )

    def test_custom_from_greater_than_to_sets_error(self):
        """custom from > to: error is not None."""
        result = resolve_range("custom", "2026-08-10", "2026-08-01", TODAY)
        assert result["error"] is not None

    def test_custom_fallback_returns_this_month_dates(self):
        """custom fallback: from_date and to_date match this_month bounds."""
        result = resolve_range("custom", "not-a-date", "2026-08-10", TODAY)
        assert result["from_date"] == "2026-08-01"
        assert result["to_date"] == TODAY.isoformat()


class TestResolveRangeInvalidKey:
    """Unknown / None range_key tests."""

    def test_unknown_key_falls_back_silently_to_this_month(self):
        """Unknown range key: silently falls back to this_month."""
        result = resolve_range("bogus", None, None, TODAY)
        assert result["active_range"] == "this_month", (
            "Unknown range key should fall back to this_month silently"
        )

    def test_unknown_key_no_error(self):
        """Unknown range key: error must be None (silent fallback)."""
        result = resolve_range("bogus", None, None, TODAY)
        assert result["error"] is None, (
            "Silent fallback from unknown key must not set an error"
        )

    def test_none_key_falls_back_to_this_month(self):
        """None range key: falls back to this_month silently."""
        result = resolve_range(None, None, None, TODAY)
        assert result["active_range"] == "this_month"
        assert result["error"] is None

    def test_empty_string_key_falls_back_to_this_month(self):
        """Empty string range key: falls back to this_month silently."""
        result = resolve_range("", None, None, TODAY)
        assert result["active_range"] == "this_month"
        assert result["error"] is None


# ===========================================================================
# 2. Query helper tests (use real SQLite with seed data)
# ===========================================================================

class TestGetSummaryStats:
    """get_summary_stats — with and without date_range."""

    def test_no_date_range_total_spent(self):
        """No date_range: total_spent matches sum of all 8 seed expenses."""
        user_id = _demo_user_id()
        stats = get_summary_stats(user_id)
        assert stats["total_spent"] == pytest.approx(SEED_TOTAL), (
            f"Expected total {SEED_TOTAL}, got {stats['total_spent']}"
        )

    def test_no_date_range_transaction_count(self):
        """No date_range: transaction_count is 8."""
        user_id = _demo_user_id()
        stats = get_summary_stats(user_id)
        assert stats["transaction_count"] == SEED_COUNT, (
            f"Expected {SEED_COUNT} transactions, got {stats['transaction_count']}"
        )

    def test_no_date_range_top_category(self):
        """No date_range: top_category is Shopping (highest single-category total)."""
        user_id = _demo_user_id()
        stats = get_summary_stats(user_id)
        assert stats["top_category"] == SEED_TOP_CATEGORY, (
            f"Expected top category '{SEED_TOP_CATEGORY}', got '{stats['top_category']}'"
        )

    def test_with_date_range_aug1_10_total_spent(self):
        """date_range Aug 1–10: total_spent is ₹2620."""
        user_id = _demo_user_id()
        stats = get_summary_stats(user_id, date_range=RANGE_AUG_1_10)
        assert stats["total_spent"] == pytest.approx(RANGE_AUG_1_10_TOTAL), (
            f"Expected ₹{RANGE_AUG_1_10_TOTAL} for Aug 1–10, got {stats['total_spent']}"
        )

    def test_with_date_range_aug1_10_transaction_count(self):
        """date_range Aug 1–10: exactly 4 transactions."""
        user_id = _demo_user_id()
        stats = get_summary_stats(user_id, date_range=RANGE_AUG_1_10)
        assert stats["transaction_count"] == RANGE_AUG_1_10_COUNT, (
            f"Expected 4 transactions for Aug 1–10, got {stats['transaction_count']}"
        )

    def test_with_date_range_aug1_10_top_category(self):
        """date_range Aug 1–10: top_category is Bills."""
        user_id = _demo_user_id()
        stats = get_summary_stats(user_id, date_range=RANGE_AUG_1_10)
        assert stats["top_category"] == RANGE_AUG_1_10_TOP, (
            f"Expected top category 'Bills' for Aug 1–10, got '{stats['top_category']}'"
        )

    def test_empty_range_zero_total(self):
        """Empty date range: total_spent is 0."""
        user_id = _demo_user_id()
        stats = get_summary_stats(user_id, date_range=EMPTY_RANGE)
        assert stats["total_spent"] == 0, (
            f"Empty range should return total 0, got {stats['total_spent']}"
        )

    def test_empty_range_zero_count(self):
        """Empty date range: transaction_count is 0."""
        user_id = _demo_user_id()
        stats = get_summary_stats(user_id, date_range=EMPTY_RANGE)
        assert stats["transaction_count"] == 0

    def test_empty_range_top_category_dash(self):
        """Empty date range: top_category is '—' (em-dash sentinel)."""
        user_id = _demo_user_id()
        stats = get_summary_stats(user_id, date_range=EMPTY_RANGE)
        assert stats["top_category"] == "—", (
            f"Empty range top_category should be '—', got '{stats['top_category']}'"
        )


class TestGetRecentTransactions:
    """get_recent_transactions — with and without date_range."""

    def test_no_date_range_returns_all_seed_expenses(self):
        """No date_range with limit=None: returns all 8 seed expenses."""
        user_id = _demo_user_id()
        txns = get_recent_transactions(user_id, limit=None)
        assert len(txns) == SEED_COUNT, (
            f"Expected {SEED_COUNT} transactions without date_range, got {len(txns)}"
        )

    def test_with_date_range_aug1_10_returns_four_transactions(self):
        """date_range Aug 1–10: returns exactly 4 transactions."""
        user_id = _demo_user_id()
        txns = get_recent_transactions(user_id, limit=None, date_range=RANGE_AUG_1_10)
        assert len(txns) == 4, (
            f"Expected 4 transactions for Aug 1–10, got {len(txns)}"
        )

    def test_with_date_range_aug1_10_sums_correctly(self):
        """date_range Aug 1–10: amounts sum to ₹2620."""
        user_id = _demo_user_id()
        txns = get_recent_transactions(user_id, limit=None, date_range=RANGE_AUG_1_10)
        total = sum(tx["amount"] for tx in txns)
        assert total == pytest.approx(RANGE_AUG_1_10_TOTAL), (
            f"Aug 1–10 transactions should sum to ₹{RANGE_AUG_1_10_TOTAL}, got {total}"
        )

    def test_with_date_range_aug1_10_categories(self):
        """date_range Aug 1–10: categories are Food, Transport, Bills, Health."""
        user_id = _demo_user_id()
        txns = get_recent_transactions(user_id, limit=None, date_range=RANGE_AUG_1_10)
        categories = {tx["category"] for tx in txns}
        assert categories == {"Food", "Transport", "Bills", "Health"}, (
            f"Expected Food/Transport/Bills/Health, got {categories}"
        )

    def test_empty_range_returns_empty_list(self):
        """Empty date range: returns []."""
        user_id = _demo_user_id()
        txns = get_recent_transactions(user_id, limit=None, date_range=EMPTY_RANGE)
        assert txns == [], (
            f"Expected empty list for empty range, got {txns}"
        )

    def test_transactions_contain_required_fields(self):
        """Each transaction dict contains date, description, category, amount."""
        user_id = _demo_user_id()
        txns = get_recent_transactions(user_id, limit=None)
        for tx in txns:
            assert "date" in tx
            assert "description" in tx
            assert "category" in tx
            assert "amount" in tx


class TestGetCategoryBreakdown:
    """get_category_breakdown — percentages and filtering."""

    def test_no_date_range_pct_sums_to_100(self):
        """No date_range: pct values sum to exactly 100."""
        user_id = _demo_user_id()
        breakdown = get_category_breakdown(user_id)
        total_pct = sum(row["pct"] for row in breakdown)
        assert total_pct == 100, (
            f"Category pcts should sum to 100 without filter, got {total_pct}"
        )

    def test_no_date_range_top_is_shopping(self):
        """No date_range: first entry (highest) is Shopping."""
        user_id = _demo_user_id()
        breakdown = get_category_breakdown(user_id)
        assert breakdown[0]["name"] == "Shopping", (
            f"Top category should be Shopping, got {breakdown[0]['name']}"
        )

    def test_with_date_range_aug1_10_top_is_bills(self):
        """date_range Aug 1–10: top category is Bills."""
        user_id = _demo_user_id()
        breakdown = get_category_breakdown(user_id, date_range=RANGE_AUG_1_10)
        assert breakdown[0]["name"] == "Bills", (
            f"Top category for Aug 1–10 should be Bills, got {breakdown[0]['name']}"
        )

    def test_with_date_range_aug1_10_pct_sums_to_100(self):
        """date_range Aug 1–10: pct values still sum to exactly 100."""
        user_id = _demo_user_id()
        breakdown = get_category_breakdown(user_id, date_range=RANGE_AUG_1_10)
        total_pct = sum(row["pct"] for row in breakdown)
        assert total_pct == 100, (
            f"Category pcts for Aug 1–10 should sum to 100, got {total_pct}"
        )

    def test_with_date_range_aug1_10_four_categories(self):
        """date_range Aug 1–10: breakdown has 4 distinct categories."""
        user_id = _demo_user_id()
        breakdown = get_category_breakdown(user_id, date_range=RANGE_AUG_1_10)
        assert len(breakdown) == 4, (
            f"Aug 1–10 breakdown should have 4 categories, got {len(breakdown)}"
        )

    def test_empty_range_returns_empty_list(self):
        """Empty date range: returns []."""
        user_id = _demo_user_id()
        breakdown = get_category_breakdown(user_id, date_range=EMPTY_RANGE)
        assert breakdown == [], (
            f"Empty date range should return [], got {breakdown}"
        )

    def test_each_breakdown_row_has_required_fields(self):
        """Each breakdown row has name, amount, pct fields."""
        user_id = _demo_user_id()
        breakdown = get_category_breakdown(user_id)
        for row in breakdown:
            assert "name" in row
            assert "amount" in row
            assert "pct" in row


# ===========================================================================
# 3. Route tests for GET /profile
# ===========================================================================

class TestProfileRoute:
    """HTTP-level tests for the /profile route."""

    def test_unauthenticated_redirects_to_login(self, client):
        """Unauthenticated /profile request: 302 redirect to /login."""
        response = client.get("/profile")
        assert response.status_code == 302, (
            f"Expected 302 for unauthenticated /profile, got {response.status_code}"
        )
        assert "/login" in response.headers.get("Location", ""), (
            "Redirect target should be /login"
        )

    def test_no_query_params_returns_200(self, logged_in_client):
        """No query params: /profile returns 200."""
        response = logged_in_client.get("/profile")
        assert response.status_code == 200, (
            f"Authenticated /profile with no params should return 200, got {response.status_code}"
        )

    def test_no_query_params_this_month_chip_is_active(self, logged_in_client):
        """No query params: 'This month' chip has is-active class."""
        response = logged_in_client.get("/profile")
        assert b"is-active" in response.data, (
            "Default (no query params) should mark 'This month' chip with is-active"
        )

    def test_no_query_params_contains_this_month_text(self, logged_in_client):
        """No query params: response contains 'This month' label text."""
        response = logged_in_client.get("/profile")
        assert b"This month" in response.data, (
            "Default /profile should display 'This month' text"
        )

    def test_range_all_returns_200(self, logged_in_client):
        """?range=all returns 200."""
        response = logged_in_client.get("/profile?range=all")
        assert response.status_code == 200

    def test_range_all_contains_rupee_symbol(self, logged_in_client):
        """?range=all: response contains ₹ symbol (project currency)."""
        response = logged_in_client.get("/profile?range=all")
        assert "₹".encode() in response.data, (
            "Profile page must use ₹ symbol, not $ (project currency is INR)"
        )

    def test_range_all_contains_total_amount(self, logged_in_client):
        """?range=all: response contains the full seed total (5,440)."""
        response = logged_in_client.get("/profile?range=all")
        # The total may be formatted as 5,440.00 or 5440.00 — match the core digits.
        assert b"5,440" in response.data or b"5440" in response.data, (
            "?range=all should show the full ₹5440 total from seed data"
        )

    def test_custom_range_aug1_10_returns_200(self, logged_in_client):
        """?range=custom&from=2026-08-01&to=2026-08-10 returns 200."""
        response = logged_in_client.get(
            "/profile?range=custom&from=2026-08-01&to=2026-08-10"
        )
        assert response.status_code == 200

    def test_custom_range_aug1_10_total_amount(self, logged_in_client):
        """?range=custom Aug 1–10: response contains ₹2,620.00."""
        response = logged_in_client.get(
            "/profile?range=custom&from=2026-08-01&to=2026-08-10"
        )
        assert b"2,620" in response.data or b"2620" in response.data, (
            "Custom Aug 1–10 range should show ₹2,620 total"
        )

    def test_custom_range_aug1_10_shows_bills_category(self, logged_in_client):
        """?range=custom Aug 1–10: response contains 'Bills' category."""
        response = logged_in_client.get(
            "/profile?range=custom&from=2026-08-01&to=2026-08-10"
        )
        assert b"Bills" in response.data, (
            "Custom Aug 1–10 range should show Bills as a category"
        )

    def test_custom_range_aug1_10_contains_rupee_symbol(self, logged_in_client):
        """?range=custom Aug 1–10: response contains ₹ symbol."""
        response = logged_in_client.get(
            "/profile?range=custom&from=2026-08-01&to=2026-08-10"
        )
        assert "₹".encode() in response.data, (
            "All amounts on profile page must use ₹ symbol"
        )

    def test_empty_date_range_shows_no_expenses_message(self, logged_in_client):
        """?range=custom with no data: shows 'No expenses in this range yet.'"""
        response = logged_in_client.get(
            "/profile?range=custom&from=2020-01-01&to=2020-01-31"
        )
        assert response.status_code == 200
        assert b"No expenses in this range yet" in response.data, (
            "An empty date range must display the no-expenses-in-range empty state"
        )

    def test_malformed_from_date_falls_back_and_shows_error(self, logged_in_client):
        """?range=custom&from=not-a-date: shows fallback error message."""
        response = logged_in_client.get(
            "/profile?range=custom&from=not-a-date&to=2026-08-10"
        )
        assert response.status_code == 200
        # The spec mandates "Showing this month instead" as the fallback phrase.
        assert b"Showing this month instead" in response.data, (
            "Malformed date should surface 'Showing this month instead' error text"
        )

    def test_last_month_url_is_shareable(self, logged_in_client):
        """?range=last_month: two identical requests return identical content."""
        url = "/profile?range=last_month"
        response_1 = logged_in_client.get(url)
        response_2 = logged_in_client.get(url)
        assert response_1.status_code == 200
        assert response_2.status_code == 200
        assert response_1.data == response_2.data, (
            "The same ?range=last_month URL should produce identical responses "
            "(URL is shareable and refresh-safe)"
        )

    def test_last_month_contains_last_month_text(self, logged_in_client):
        """?range=last_month: response contains 'Last month'."""
        response = logged_in_client.get("/profile?range=last_month")
        assert b"Last month" in response.data, (
            "?range=last_month should display 'Last month' text in page"
        )

    def test_every_profile_response_contains_rupee_symbol(self, logged_in_client):
        """All profile URL variations contain the ₹ symbol (INR project currency)."""
        urls = [
            "/profile",
            "/profile?range=all",
            "/profile?range=last_7_days",
            "/profile?range=last_30_days",
            "/profile?range=custom&from=2026-08-01&to=2026-08-10",
        ]
        rupee = "₹".encode()
        for url in urls:
            response = logged_in_client.get(url)
            assert response.status_code == 200, f"Expected 200 for {url}"
            assert rupee in response.data, (
                f"₹ symbol missing from {url} — project currency is INR"
            )

    def test_last_7_days_chip_active(self, logged_in_client):
        """?range=last_7_days: 'Last 7 days' chip is marked active."""
        response = logged_in_client.get("/profile?range=last_7_days")
        assert response.status_code == 200
        assert b"is-active" in response.data, (
            "?range=last_7_days should mark the Last 7 days chip with is-active"
        )
        assert b"Last 7 days" in response.data, (
            "?range=last_7_days should display 'Last 7 days' text"
        )

    def test_unknown_range_key_defaults_to_this_month(self, logged_in_client):
        """?range=bogus: server falls back to this_month silently, no 500."""
        response = logged_in_client.get("/profile?range=bogus")
        assert response.status_code == 200, (
            "Unknown range key should not cause a 500 error"
        )
        assert b"This month" in response.data, (
            "Unknown range key should fall back to 'This month'"
        )
