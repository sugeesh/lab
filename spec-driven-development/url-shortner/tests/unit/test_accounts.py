import hashlib
from datetime import UTC, datetime, timedelta

import pytest

from shortener import accounts, db

NOW = datetime(2026, 11, 17, 12, 0, tzinfo=UTC)


@pytest.fixture
def conn(tmp_path):
    connection = db.connect(str(tmp_path / "t.db"))
    db.init_schema(connection)
    yield connection
    connection.close()


def test_password_hash_round_trip():
    stored = accounts.hash_password("password123")

    assert accounts.verify_password("password123", stored)
    assert not accounts.verify_password("password124", stored)


def test_same_password_hashes_differently():
    assert accounts.hash_password("password123") != accounts.hash_password("password123")


def test_create_user_lowercases_email(conn):
    user_id = accounts.create_user(conn, "Alice@Example.COM", "password123", "UTC", NOW)

    row = conn.execute("SELECT email FROM users WHERE id = ?", (user_id,)).fetchone()
    assert row["email"] == "alice@example.com"


@pytest.mark.parametrize(
    ("email", "password", "message"),
    [
        ("no-at-sign", "password123", "Enter a valid email address."),
        ("a" * 250 + "@x.io", "password123", "Enter a valid email address."),
        ("alice@example.com", "short", "Use a password with at least 8 characters."),
    ],
)
def test_create_user_rejects_bad_input(conn, email, password, message):
    with pytest.raises(accounts.AccountError, match=message):
        accounts.create_user(conn, email, password, "UTC", NOW)


def test_create_user_rejects_duplicate_email_case_insensitively(conn):
    accounts.create_user(conn, "alice@example.com", "password123", "UTC", NOW)

    with pytest.raises(accounts.AccountError, match="already has an account"):
        accounts.create_user(conn, "ALICE@example.com", "password123", "UTC", NOW)


@pytest.mark.parametrize(
    ("given", "expected"),
    [("Asia/Colombo", "Asia/Colombo"), ("", "UTC"), ("Mars/Olympus", "UTC"), (None, "UTC")],
)
def test_normalize_time_zone(given, expected):
    assert accounts.normalize_time_zone(given) == expected


def test_authenticate(conn):
    user_id = accounts.create_user(conn, "alice@example.com", "password123", "UTC", NOW)

    assert accounts.authenticate(conn, "ALICE@example.com", "password123")["id"] == user_id
    assert accounts.authenticate(conn, "alice@example.com", "wrong-pass") is None
    assert accounts.authenticate(conn, "nobody@example.com", "password123") is None


def test_session_lifecycle(conn):
    user_id = accounts.create_user(conn, "alice@example.com", "password123", "UTC", NOW)

    token = accounts.create_session(conn, user_id, NOW)

    stored = conn.execute("SELECT token_hash FROM sessions").fetchone()["token_hash"]
    assert stored == hashlib.sha256(token.encode()).hexdigest()
    assert stored != token
    assert accounts.user_for_session(conn, token, NOW + timedelta(days=13))["id"] == user_id
    assert accounts.user_for_session(conn, token, NOW + timedelta(days=14)) is None

    accounts.delete_session(conn, token)
    assert accounts.user_for_session(conn, token, NOW) is None


def test_user_for_session_with_unknown_token(conn):
    assert accounts.user_for_session(conn, "nope", NOW) is None
    assert accounts.user_for_session(conn, None, NOW) is None


def test_update_time_zone(conn):
    user_id = accounts.create_user(conn, "alice@example.com", "password123", "UTC", NOW)

    accounts.update_time_zone(conn, user_id, "Asia/Colombo")

    row = conn.execute("SELECT time_zone FROM users WHERE id = ?", (user_id,)).fetchone()
    assert row["time_zone"] == "Asia/Colombo"
