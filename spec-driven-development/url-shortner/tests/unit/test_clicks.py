from datetime import UTC, date, datetime

import pytest

from shortener import accounts, clicks, db, links

NOW = datetime(2026, 11, 17, 20, 0, tzinfo=UTC)  # already 18 Nov in Colombo (+05:30)


@pytest.fixture
def conn(tmp_path):
    connection = db.connect(str(tmp_path / "t.db"))
    db.init_schema(connection)
    yield connection
    connection.close()


@pytest.fixture
def code(conn):
    user_id = accounts.create_user(conn, "alice@example.com", "password123", "UTC", NOW)
    return links.create_link(conn, user_id, "https://example.com", "short.test", NOW)


def day_rows(conn, code):
    rows = conn.execute("SELECT day, count FROM daily_clicks WHERE code = ?", (code,))
    return [tuple(row) for row in rows]


def test_record_click_creates_then_increments_the_day_row(conn, code):
    clicks.record_click(conn, code, "UTC", NOW)
    assert day_rows(conn, code) == [("2026-11-17", 1)]

    clicks.record_click(conn, code, "UTC", NOW)
    assert day_rows(conn, code) == [("2026-11-17", 2)]


def test_day_is_taken_in_the_owner_time_zone(conn, code):
    clicks.record_click(conn, code, "Asia/Colombo", NOW)

    assert day_rows(conn, code) == [("2026-11-18", 1)]


def test_total_clicks(conn, code):
    assert clicks.total_clicks(conn, code) == 0

    conn.execute("INSERT INTO daily_clicks VALUES (?, '2025-01-01', 4)", (code,))
    clicks.record_click(conn, code, "UTC", NOW)

    assert clicks.total_clicks(conn, code) == 5


def test_last_30_days_fills_zeros_oldest_first(conn, code):
    conn.execute("INSERT INTO daily_clicks VALUES (?, '2026-11-18', 5)", (code,))
    conn.execute("INSERT INTO daily_clicks VALUES (?, '2026-11-17', 3)", (code,))
    conn.execute("INSERT INTO daily_clicks VALUES (?, '2026-10-19', 9)", (code,))  # 31st day

    series = clicks.last_30_days(conn, code, "Asia/Colombo", NOW)

    assert len(series) == 30
    assert series[0] == (date(2026, 10, 20), 0)
    assert series[-1] == (date(2026, 11, 18), 5)
    assert series[-2] == (date(2026, 11, 17), 3)
    assert sum(count for _, count in series) == 8
