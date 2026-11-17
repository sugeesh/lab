import sqlite3
from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends, Request
from fastapi.templating import Jinja2Templates

from shortener import accounts, db
from shortener.config import Settings

SESSION_COOKIE = "session"


class SignInRequired(Exception):
    def __init__(self, next_path: str):
        self.next_path = next_path


def now() -> datetime:
    return datetime.now(UTC)


def settings(request: Request) -> Settings:
    return request.app.state.settings


def templates(request: Request) -> Jinja2Templates:
    return request.app.state.templates


def get_conn(request: Request) -> Iterator[sqlite3.Connection]:
    conn = db.connect(settings(request).db_path)
    try:
        yield conn
    finally:
        conn.close()


Conn = Annotated[sqlite3.Connection, Depends(get_conn)]


def current_user(request: Request, conn: Conn) -> sqlite3.Row | None:
    return accounts.user_for_session(conn, request.cookies.get(SESSION_COOKIE), now())


def require_user(request: Request, conn: Conn) -> sqlite3.Row:
    user = current_user(request, conn)
    if user is None:
        # POST-only paths have no page to come back to, so only GETs keep their path.
        raise SignInRequired(request.url.path if request.method == "GET" else "/")
    return user


User = Annotated[sqlite3.Row, Depends(require_user)]
MaybeUser = Annotated[sqlite3.Row | None, Depends(current_user)]


def render(request: Request, name: str, context: dict | None = None, status_code: int = 200):
    return templates(request).TemplateResponse(
        request, name, context or {}, status_code=status_code
    )
