import hashlib
import hmac
import secrets
import sqlite3
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from shortener.db import to_text

EMAIL_MAX_LENGTH = 254
PASSWORD_MIN_LENGTH = 8
SESSION_LIFETIME = timedelta(days=14)
_SCRYPT = {"n": 2**14, "r": 8, "p": 1}


class AccountError(ValueError):
    pass


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, **_SCRYPT)
    return f"scrypt${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    _, salt_hex, digest_hex = stored.split("$")
    digest = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt_hex), **_SCRYPT)
    return hmac.compare_digest(digest.hex(), digest_hex)


def normalize_time_zone(name: str | None) -> str:
    if not name:
        return "UTC"
    try:
        ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError):
        return "UTC"
    return name


def _normalize_email(email: str) -> str:
    email = email.strip().lower()
    local, at, domain = email.rpartition("@")
    if not at or not local or not domain or len(email) > EMAIL_MAX_LENGTH:
        raise AccountError("Enter a valid email address.")
    return email


def create_user(
    conn: sqlite3.Connection, email: str, password: str, time_zone: str | None, now: datetime
) -> int:
    email = _normalize_email(email)
    if len(password) < PASSWORD_MIN_LENGTH:
        raise AccountError("Use a password with at least 8 characters.")
    try:
        cursor = conn.execute(
            "INSERT INTO users (email, password_hash, time_zone, created_at) VALUES (?, ?, ?, ?)",
            (email, hash_password(password), normalize_time_zone(time_zone), to_text(now)),
        )
    except sqlite3.IntegrityError:
        raise AccountError("That email already has an account. Sign in instead.") from None
    return cursor.lastrowid


def authenticate(conn: sqlite3.Connection, email: str, password: str) -> sqlite3.Row | None:
    user = conn.execute("SELECT * FROM users WHERE email = ?", (email.strip().lower(),)).fetchone()
    if user is None or not verify_password(password, user["password_hash"]):
        return None
    return user


def update_time_zone(conn: sqlite3.Connection, user_id: int, time_zone: str | None) -> None:
    conn.execute(
        "UPDATE users SET time_zone = ? WHERE id = ?", (normalize_time_zone(time_zone), user_id)
    )


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_session(conn: sqlite3.Connection, user_id: int, now: datetime) -> str:
    token = secrets.token_urlsafe(32)
    conn.execute(
        "INSERT INTO sessions (token_hash, user_id, expires_at) VALUES (?, ?, ?)",
        (_token_hash(token), user_id, to_text(now + SESSION_LIFETIME)),
    )
    return token


def user_for_session(
    conn: sqlite3.Connection, token: str | None, now: datetime
) -> sqlite3.Row | None:
    if not token:
        return None
    return conn.execute(
        "SELECT users.* FROM sessions JOIN users ON users.id = sessions.user_id "
        "WHERE sessions.token_hash = ? AND sessions.expires_at > ?",
        (_token_hash(token), to_text(now)),
    ).fetchone()


def delete_session(conn: sqlite3.Connection, token: str | None) -> None:
    if token:
        conn.execute("DELETE FROM sessions WHERE token_hash = ?", (_token_hash(token),))
