import re

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from shortener import links
from shortener.web.deps import Conn, render

router = APIRouter()

CODE_PATTERN = re.compile(r"[A-Za-z0-9]{7}")


@router.get("/{code}")
def follow_short_link(request: Request, code: str, conn: Conn):
    link = links.find_for_redirect(conn, code) if CODE_PATTERN.fullmatch(code) else None
    if link is None:
        return render(request, "visitor_not_found.html", status_code=404)
    return RedirectResponse(
        link["target_url"], status_code=302, headers={"Cache-Control": "no-store"}
    )
