from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse

from shortener import clicks, links
from shortener.codes import CodeExhaustedError
from shortener.db import from_text
from shortener.links import ExpiryError, RateLimitError
from shortener.urls import UrlError
from shortener.web.deps import Conn, User, in_zone, now, render, settings

router = APIRouter()

STATUS_LABELS = {"active": "Active", "disabled": "Disabled", "expired": "Expired"}


def _local(moment: datetime, time_zone: str) -> datetime:
    return in_zone(moment, time_zone)[0]


def _link_view(request: Request, link, user, moment: datetime) -> dict:
    """Everything a template shows about one link, already in the owner's time zone."""
    expires_at = link["expires_at"]
    local_expiry, expires_zone = (
        in_zone(from_text(expires_at), user["time_zone"]) if expires_at else (None, None)
    )
    return {
        "code": link["code"],
        "short_link": f"{settings(request).base_url}/{link['code']}",
        "target_url": link["target_url"],
        "enabled": bool(link["enabled"]),
        "status": STATUS_LABELS[links.status(link["enabled"], expires_at, moment)],
        "expires_at": local_expiry,
        "expires_zone": expires_zone,
        "expires_at_input": local_expiry.strftime("%Y-%m-%dT%H:%M") if local_expiry else "",
        "created_at": _local(from_text(link["created_at"]), user["time_zone"]),
    }


def _home(request: Request, conn, user, form: dict | None = None, error: str = "", status=200):
    moment = now()
    rows = [
        {**_link_view(request, link, user, moment), "total_clicks": link["total_clicks"]}
        for link in links.list_links(conn, user["id"])
    ]
    context = {"user": user, "links": rows, "form": form or {}, "error": error}
    return render(request, "home.html", context, status)


def _owned_or_404(request: Request, conn, user, code: str):
    link = links.get_owned_link(conn, user["id"], code)
    if link is None:
        return None, render(request, "visitor_not_found.html", {"user": user}, 404)
    return link, None


def _back_to(code: str) -> RedirectResponse:
    return RedirectResponse(f"/links/{code}", status_code=303)


@router.get("/")
def home(request: Request, conn: Conn, user: User):
    return _home(request, conn, user)


FormText = Annotated[str, Form()]


@router.post("/links")
def create(request: Request, conn: Conn, user: User, url: FormText = "", expires_at: FormText = ""):
    form = {"url": url, "expires_at": expires_at}
    moment = now()
    try:
        expiry = links.parse_local_expiry(expires_at, user["time_zone"], moment)
        code = links.create_link(
            conn, user["id"], url, settings(request).host, moment, expires_at=expiry
        )
    except (UrlError, ExpiryError) as error:
        return _home(request, conn, user, form, str(error), 400)
    except RateLimitError as limit:
        retry_at = _local(limit.retry_at, user["time_zone"]).strftime("%H:%M")
        message = f"You've created 100 links in the last hour. You can create more at {retry_at}."
        return _home(request, conn, user, form, message, 429)
    except CodeExhaustedError:
        message = "We couldn't create a short link just now. Please try again."
        return _home(request, conn, user, form, message, 503)
    return _back_to(code)


def _detail(request: Request, conn, link, user, expiry_error: str = "", status: int = 200):
    moment = now()
    days = clicks.last_30_days(conn, link["code"], user["time_zone"], moment)
    busiest = max(count for _, count in days)
    context = {
        "user": user,
        "link": _link_view(request, link, user, moment),
        "expiry_error": expiry_error,
        "total_clicks": clicks.total_clicks(conn, link["code"]),
        "days": [
            {"day": day, "count": count, "share": count / busiest if busiest else 0}
            for day, count in days
        ],
    }
    return render(request, "link.html", context, status)


@router.get("/links/{code}")
def detail(request: Request, code: str, conn: Conn, user: User):
    link, not_found = _owned_or_404(request, conn, user, code)
    return not_found or _detail(request, conn, link, user)


@router.post("/links/{code}/expiry")
def change_expiry(request: Request, code: str, conn: Conn, user: User, expires_at: FormText = ""):
    link, not_found = _owned_or_404(request, conn, user, code)
    if not_found:
        return not_found
    try:
        expiry = links.parse_local_expiry(expires_at, user["time_zone"], now())
    except ExpiryError as error:
        return _detail(request, conn, link, user, str(error), 400)
    links.set_expiry(conn, user["id"], code, expiry)
    return _back_to(code)


@router.post("/links/{code}/disable")
def disable(request: Request, code: str, conn: Conn, user: User):
    if not links.set_enabled(conn, user["id"], code, enabled=False):
        return render(request, "visitor_not_found.html", {"user": user}, 404)
    return _back_to(code)


@router.post("/links/{code}/enable")
def enable(request: Request, code: str, conn: Conn, user: User):
    if not links.set_enabled(conn, user["id"], code, enabled=True):
        return render(request, "visitor_not_found.html", {"user": user}, 404)
    return _back_to(code)


@router.get("/links/{code}/delete")
def confirm_delete(request: Request, code: str, conn: Conn, user: User):
    link, not_found = _owned_or_404(request, conn, user, code)
    if not_found:
        return not_found
    context = {"user": user, "link": _link_view(request, link, user, now())}
    return render(request, "delete.html", context)


@router.post("/links/{code}/delete")
def delete(request: Request, code: str, conn: Conn, user: User):
    if not links.delete_link(conn, user["id"], code):
        return render(request, "visitor_not_found.html", {"user": user}, 404)
    return RedirectResponse("/", status_code=303)
