import logging
import re
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Request
from fastapi.responses import RedirectResponse

from shortener import clicks, db, links
from shortener.db import from_text
from shortener.web.deps import Conn, in_zone, now, render, settings

logger = logging.getLogger(__name__)
router = APIRouter()

CODE_PATTERN = re.compile(r"[A-Za-z0-9]{7}")


def _record_click_safely(db_path: str, code: str, time_zone: str, moment: datetime) -> None:
    """Runs after the redirect is sent. A failure is logged and the click is lost (FR-018a)."""
    try:
        conn = db.connect(db_path)
        try:
            clicks.record_click(conn, code, time_zone, moment)
        finally:
            conn.close()
    except Exception:
        logger.exception("click not recorded for code %s", code)


@router.get("/{code}")
def follow_short_link(request: Request, code: str, conn: Conn, background: BackgroundTasks):
    link = links.find_for_redirect(conn, code) if CODE_PATTERN.fullmatch(code) else None
    if link is None:
        return render(request, "visitor_not_found.html", status_code=404)
    moment = now()
    state = links.status(link["enabled"], link["expires_at"], moment)
    if state == "disabled":
        return render(request, "visitor_disabled.html", status_code=403)
    if state == "expired":
        expired_at, zone = in_zone(from_text(link["expires_at"]), link["time_zone"])
        context = {"expired_at": expired_at, "time_zone": zone}
        return render(request, "visitor_expired.html", context, 410)
    background.add_task(
        _record_click_safely, settings(request).db_path, code, link["time_zone"], moment
    )
    return RedirectResponse(
        link["target_url"], status_code=302, headers={"Cache-Control": "no-store"}
    )
