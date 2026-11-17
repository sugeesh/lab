from datetime import UTC, datetime, timedelta

import pytest

from shortener import accounts, db, links

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


def issue_codes(conn, user_id, count, first_at):
    conn.executemany(
        "INSERT INTO issued_codes (code, user_id, issued_at) VALUES (?, ?, ?)",
        [(f"R{i:06d}", user_id, db.to_text(first_at + timedelta(seconds=i))) for i in range(count)],
    )


def test_allowed_under_the_limit(conn, user_id):
    issue_codes(conn, user_id, 99, NOW - timedelta(minutes=50))

    links.check_creation_allowed(conn, user_id, NOW)


def test_refused_at_the_limit_with_retry_time(conn, user_id):
    issue_codes(conn, user_id, 100, NOW - timedelta(minutes=50))

    with pytest.raises(links.RateLimitError) as refused:
        links.check_creation_allowed(conn, user_id, NOW)

    assert refused.value.retry_at == NOW + timedelta(minutes=10)


def test_codes_older_than_an_hour_do_not_count(conn, user_id):
    issue_codes(conn, user_id, 100, NOW - timedelta(minutes=90))

    links.check_creation_allowed(conn, user_id, NOW)
