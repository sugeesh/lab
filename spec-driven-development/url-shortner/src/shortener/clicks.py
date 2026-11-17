import sqlite3
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

DAYS_SHOWN = 30


def _local_day(moment: datetime, time_zone: str) -> date:
    return moment.astimezone(ZoneInfo(time_zone)).date()


def record_click(conn: sqlite3.Connection, code: str, owner_time_zone: str, now: datetime) -> None:
    """One successful redirect: one upsert into the owner's calendar day."""
    conn.execute(
        "INSERT INTO daily_clicks (code, day, count) VALUES (?, ?, 1) "
        "ON CONFLICT (code, day) DO UPDATE SET count = count + 1",
        (code, _local_day(now, owner_time_zone).isoformat()),
    )


def total_clicks(conn: sqlite3.Connection, code: str) -> int:
    row = conn.execute(
        "SELECT COALESCE(SUM(count), 0) FROM daily_clicks WHERE code = ?", (code,)
    ).fetchone()
    return row[0]


def last_30_days(
    conn: sqlite3.Connection, code: str, owner_time_zone: str, now: datetime
) -> list[tuple[date, int]]:
    """Oldest first, today last, zero for days without clicks."""
    today = _local_day(now, owner_time_zone)
    days = [today - timedelta(days=offset) for offset in range(DAYS_SHOWN - 1, -1, -1)]
    rows = conn.execute(
        "SELECT day, count FROM daily_clicks WHERE code = ? AND day BETWEEN ? AND ?",
        (code, days[0].isoformat(), today.isoformat()),
    )
    counts = {row["day"]: row["count"] for row in rows}
    return [(day, counts.get(day.isoformat(), 0)) for day in days]
