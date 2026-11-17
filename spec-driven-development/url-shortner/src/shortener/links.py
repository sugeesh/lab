import sqlite3
from datetime import datetime, timedelta

from shortener import codes
from shortener.db import from_text, to_text, transaction
from shortener.urls import validate_target_url

CREATION_LIMIT = 100
CREATION_WINDOW = timedelta(minutes=60)


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
) -> str:
    target_url = validate_target_url(target_url, service_host)
    with transaction(conn):
        check_creation_allowed(conn, user_id, now)
        code = codes.issue_code(conn, user_id, now)
        conn.execute(
            "INSERT INTO links (code, user_id, target_url, created_at) VALUES (?, ?, ?, ?)",
            (code, user_id, target_url, to_text(now)),
        )
    return code


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
