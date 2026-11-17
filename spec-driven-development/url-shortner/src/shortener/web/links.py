from typing import Annotated
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse

from shortener import links
from shortener.db import from_text
from shortener.links import RateLimitError
from shortener.urls import UrlError
from shortener.web.deps import Conn, User, now, render, settings

router = APIRouter()


def _local(moment, time_zone: str):
    return moment.astimezone(ZoneInfo(time_zone))


@router.get("/")
def home(request: Request, user: User):
    return render(request, "home.html", {"user": user})


@router.post("/links")
def create(request: Request, conn: Conn, user: User, url: Annotated[str, Form()] = ""):
    try:
        code = links.create_link(conn, user["id"], url, settings(request).host, now())
    except UrlError as error:
        return render(request, "home.html", {"user": user, "url": url, "error": str(error)}, 400)
    except RateLimitError as limit:
        retry_at = _local(limit.retry_at, user["time_zone"]).strftime("%H:%M")
        message = f"You've created 100 links in the last hour. You can create more at {retry_at}."
        return render(request, "home.html", {"user": user, "url": url, "error": message}, 429)
    return RedirectResponse(f"/links/{code}", status_code=303)


@router.get("/links/{code}")
def detail(request: Request, code: str, conn: Conn, user: User):
    link = links.get_owned_link(conn, user["id"], code)
    if link is None:
        return render(request, "visitor_not_found.html", {"user": user}, 404)
    context = {
        "user": user,
        "link": link,
        "short_link": f"{settings(request).base_url}/{code}",
        "created_at": _local(from_text(link["created_at"]), user["time_zone"]),
    }
    return render(request, "link.html", context)
