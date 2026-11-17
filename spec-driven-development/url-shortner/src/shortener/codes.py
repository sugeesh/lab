import secrets
import sqlite3
import string
from collections.abc import Callable
from datetime import datetime

from shortener.db import to_text

ALPHABET = string.ascii_letters + string.digits
CODE_LENGTH = 7
MAX_ATTEMPTS = 5


class CodeExhaustedError(RuntimeError):
    pass


def generate_code() -> str:
    return "".join(secrets.choice(ALPHABET) for _ in range(CODE_LENGTH))


def issue_code(
    conn: sqlite3.Connection,
    user_id: int,
    now: datetime,
    generate: Callable[[], str] = generate_code,
) -> str:
    """Reserve a never-before-issued code. issued_codes rows are never deleted."""
    for _ in range(MAX_ATTEMPTS):
        code = generate()
        try:
            conn.execute(
                "INSERT INTO issued_codes (code, user_id, issued_at) VALUES (?, ?, ?)",
                (code, user_id, to_text(now)),
            )
        except sqlite3.IntegrityError:
            continue
        return code
    raise CodeExhaustedError(f"no free code after {MAX_ATTEMPTS} attempts")
