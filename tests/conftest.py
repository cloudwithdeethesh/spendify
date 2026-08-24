import os
import sys
import tempfile
from pathlib import Path

import pytest

# Redirect DB_PATH BEFORE app is imported so the module-level init_db()/seed_db()
# in app.py lands in a throwaway temp file instead of the real spendly.db.
_TEMP_DB_FD, _TEMP_DB_PATH = tempfile.mkstemp(suffix="-spendly-test.db")
os.close(_TEMP_DB_FD)

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import database.db as _db_module  # noqa: E402

_db_module.DB_PATH = Path(_TEMP_DB_PATH)

from app import app as flask_app  # noqa: E402
from database.db import create_user, get_db  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _cleanup_temp_db():
    yield
    try:
        os.unlink(_TEMP_DB_PATH)
    except FileNotFoundError:
        pass


@pytest.fixture(scope="session")
def app():
    flask_app.config["TESTING"] = True
    return flask_app


@pytest.fixture(scope="session")
def seed_user_id(app):
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT id FROM users WHERE email = ?", ("demo@spendly.com",)
        ).fetchone()
    finally:
        conn.close()
    return row["id"]


@pytest.fixture(scope="session")
def empty_user_id(app):
    create_user("Empty User", "empty@spendly.com", "password123")
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT id FROM users WHERE email = ?", ("empty@spendly.com",)
        ).fetchone()
    finally:
        conn.close()
    return row["id"]


@pytest.fixture()
def client(app, seed_user_id):
    with app.test_client() as c:
        with c.session_transaction() as sess:
            sess["user_id"] = seed_user_id
            sess["user_name"] = "Demo User"
        yield c
