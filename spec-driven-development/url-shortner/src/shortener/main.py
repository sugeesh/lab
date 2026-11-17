import logging
import time
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from shortener import db
from shortener.config import Settings
from shortener.web import account, links, redirect
from shortener.web.deps import SignInRequired

PACKAGE_DIR = Path(__file__).parent


class ServerTimingMiddleware:
    """Adds `Server-Timing: app;dur=<ms>`, measured until the response headers are sent."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        started = time.perf_counter()

        async def send_with_timing(message):
            if message["type"] == "http.response.start":
                duration_ms = (time.perf_counter() - started) * 1000
                header = (b"server-timing", f"app;dur={duration_ms:.2f}".encode())
                message = {**message, "headers": [*message.get("headers", []), header]}
            await send(message)

        await self.app(scope, receive, send_with_timing)


def _redirect_to_sign_in(request: Request, exc: SignInRequired) -> RedirectResponse:
    return RedirectResponse(f"/account/signin?next={exc.next_path}", status_code=303)


def create_app(db_path: str | None = None, base_url: str | None = None) -> FastAPI:
    """App factory. Run with: uvicorn shortener.main:create_app --factory"""
    logging.basicConfig(level=logging.INFO)
    defaults = Settings.from_env()
    settings = Settings(
        db_path=db_path or defaults.db_path,
        base_url=(base_url or defaults.base_url).rstrip("/"),
    )
    conn = db.connect(settings.db_path)
    db.init_schema(conn)
    conn.close()

    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    app.state.settings = settings
    app.state.templates = Jinja2Templates(directory=PACKAGE_DIR / "templates")
    app.add_middleware(ServerTimingMiddleware)
    app.add_exception_handler(SignInRequired, _redirect_to_sign_in)
    app.mount("/static", StaticFiles(directory=PACKAGE_DIR / "static"), name="static")
    app.include_router(account.router)
    app.include_router(links.router)
    app.include_router(redirect.router)  # last: /{code} must never shadow an app page
    return app
