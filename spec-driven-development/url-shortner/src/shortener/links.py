import sqlite3
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from shortener import codes
from shortener.db import from_text, to_text, transaction
from shortener.urls import validate_target_url

CREATION_LIMIT = 100
CREATION_WINDOW = timedelta(minutes=60)
LAST_YEAR = 9999


class ExpiryError(ValueError):
    pass


def parse_local_expiry(value: str, time_zone: str, now: datetime) -> str | None:
    """Turn a browser `datetime-local` value in the owner's zone into stored UTC text."""
    value = value.strip()
    if not value:
        return None
    try:
        local = datetime.fromisoformat(value)
    except ValueError:
        raise ExpiryError("Enter the expiry as a date and a time.") from None
    if local.tzinfo is not None or "T" not in value:
        raise ExpiryError("Enter the expiry as a date and a time.")
    if local.year >= LAST_YEAR:
        # Keeps every stored expiry displayable in every time zone (UTC-12 to UTC+14).
        raise ExpiryError("Choose a date before the year 9999.")
    expires_at = local.replace(tzinfo=ZoneInfo(time_zone))
    if expires_at <= now:
        raise ExpiryError("Choose a time in the future.")
    return to_text(expires_at)


class RateLimitError(Exception):
    def __init__(self, retry_at: datetime):
        super().__init__(f"creation limit reached until {retry_at:%H:%M}")
        self.retry_at = retry_at


def check_creation_allowed(conn: sqlite3.Connection, user_id: int, now: datetime) -> None:
    # The CREATION_LIMIT-th most recent code in the window; once it ages out, one slot frees up.
    row = conn.execute(
        "SELECT issued_at FROM issued_codes WHERE user_id = ? AND issued_at > ? "
        "ORDER BY issued_at DESC LIMIT 1 OFFSET ?",
        (user_id, to_text(now - CREATION_WINDOW), CREATION_LIMIT - 1),
    ).fetchone()
    if row is not None:
        raise RateLimitError(from_text(row["issued_at"]) + CREATION_WINDOW)


def create_link(
    conn: sqlite3.Connection,
    user_id: int,
    target_url: str,
    service_host: str,
    now: datetime,
    expires_at: str | None = None,
) -> str:
    target_url = validate_target_url(target_url, service_host)
    with transaction(conn):
        check_creation_allowed(conn, user_id, now)
        code = codes.issue_code(conn, user_id, now)
        conn.execute(
            "INSERT INTO links (code, user_id, target_url, expires_at, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (code, user_id, target_url, expires_at, to_text(now)),
        )
    return code


def status(enabled: int, expires_at: str | None, now: datetime) -> str:
    """Disabled wins over expired: the owner's explicit choice is what visitors see."""
    if not enabled:
        return "disabled"
    if expires_at is not None and expires_at <= to_text(now):
        return "expired"
    return "active"


def list_links(conn: sqlite3.Connection, user_id: int) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT l.*, COALESCE(SUM(c.count), 0) AS total_clicks "
        "FROM links l LEFT JOIN daily_clicks c ON c.code = l.code "
        "WHERE l.user_id = ? GROUP BY l.code "
        "ORDER BY l.created_at DESC, l.rowid DESC",
        (user_id,),
    ).fetchall()


def set_enabled(conn: sqlite3.Connection, user_id: int, code: str, enabled: bool) -> bool:
    cursor = conn.execute(
        "UPDATE links SET enabled = ? WHERE code = ? AND user_id = ?",
        (int(enabled), code, user_id),
    )
    return cursor.rowcount == 1


def set_expiry(conn: sqlite3.Connection, user_id: int, code: str, expires_at: str | None) -> bool:
    cursor = conn.execute(
        "UPDATE links SET expires_at = ? WHERE code = ? AND user_id = ?",
        (expires_at, code, user_id),
    )
    return cursor.rowcount == 1


def delete_link(conn: sqlite3.Connection, user_id: int, code: str) -> bool:
    """Clicks go with the link (ON DELETE CASCADE); the issued code is kept forever."""
    cursor = conn.execute("DELETE FROM links WHERE code = ? AND user_id = ?", (code, user_id))
    return cursor.rowcount == 1


def get_owned_link(conn: sqlite3.Connection, user_id: int, code: str) -> sqlite3.Row | None:
    """Another user's link is indistinguishable from a missing one (FR-003)."""
    return conn.execute(
        "SELECT * FROM links WHERE code = ? AND user_id = ?", (code, user_id)
    ).fetchone()


def find_for_redirect(conn: sqlite3.Connection, code: str) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT l.target_url, l.enabled, l.expires_at, u.time_zone "
        "FROM links l JOIN users u ON u.id = l.user_id WHERE l.code = ?",
        (code,),
    ).fetchone()
