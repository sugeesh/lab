import string
from datetime import UTC, datetime

import pytest

from shortener import accounts, codes, db

NOW = datetime(2026, 11, 17, 12, 0, tzinfo=UTC)


@pytest.fixture
def conn(tmp_path):
    connection = db.connect(str(tmp_path / "t.db"))
    db.init_schema(connection)
    yield connection
    connection.close()


@pytest.fixture
def user_id(conn):
    return accounts.create_user(conn, "alice@example.com", "password123", "UTC", NOW)


def test_generated_code_is_seven_alphanumeric_characters():
    for _ in range(200):
        code = codes.generate_code()
        assert len(code) == 7
        assert set(code) <= set(string.ascii_letters + string.digits)


def test_issue_code_records_the_code(conn, user_id):
    code = codes.issue_code(conn, user_id, NOW)

    row = conn.execute("SELECT * FROM issued_codes WHERE code = ?", (code,)).fetchone()
    assert row["user_id"] == user_id
    assert row["issued_at"] == "2026-11-17T12:00:00Z"


def test_issue_code_retries_when_code_was_issued_before(conn, user_id):
    codes.issue_code(conn, user_id, NOW, generate=lambda: "AAAAAAA")
    candidates = iter(["AAAAAAA", "BBBBBBB"])

    code = codes.issue_code(conn, user_id, NOW, generate=lambda: next(candidates))

    assert code == "BBBBBBB"


def test_issue_code_gives_up_after_five_collisions(conn, user_id):
    codes.issue_code(conn, user_id, NOW, generate=lambda: "AAAAAAA")
    attempts = []

    def always_taken():
        attempts.append(1)
        return "AAAAAAA"

    with pytest.raises(codes.CodeExhaustedError):
        codes.issue_code(conn, user_id, NOW, generate=always_taken)
    assert len(attempts) == 5
