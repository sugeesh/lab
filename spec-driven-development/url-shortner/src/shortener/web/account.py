from typing import Annotated

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse

from shortener import accounts
from shortener.accounts import SESSION_LIFETIME, AccountError
from shortener.web.deps import SESSION_COOKIE, Conn, MaybeUser, now, render, settings

router = APIRouter(prefix="/account")

FormText = Annotated[str, Form()]


def _safe_next(next_path: str) -> str:
    """Only allow local paths, so sign-in can never send someone to another site."""
    if next_path.startswith("/") and not next_path.startswith("//"):
        return next_path
    return "/"


def _start_session(request: Request, conn, user_id: int, target: str) -> RedirectResponse:
    token = accounts.create_session(conn, user_id, now())
    response = RedirectResponse(target, status_code=303)
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=int(SESSION_LIFETIME.total_seconds()),
        httponly=True,
        samesite="lax",
        secure=settings(request).secure_cookies,
    )
    return response


@router.get("/signup")
def signup_form(request: Request, user: MaybeUser):
    return render(request, "signup.html", {"user": user})


@router.post("/signup")
def signup(
    request: Request,
    conn: Conn,
    email: FormText = "",
    password: FormText = "",
    time_zone: FormText = "",
):
    try:
        user_id = accounts.create_user(conn, email, password, time_zone, now())
    except AccountError as error:
        return render(request, "signup.html", {"error": str(error), "email": email}, 400)
    return _start_session(request, conn, user_id, "/")


@router.get("/signin")
def signin_form(request: Request, user: MaybeUser, next: str = "/"):
    return render(request, "signin.html", {"user": user, "next": _safe_next(next)})


@router.post("/signin")
def signin(
    request: Request,
    conn: Conn,
    email: FormText = "",
    password: FormText = "",
    time_zone: FormText = "",
    next: FormText = "",
):
    user = accounts.authenticate(conn, email, password)
    if user is None:
        context = {"error": "Email or password is incorrect.", "email": email, "next": next}
        return render(request, "signin.html", context, 400)
    accounts.update_time_zone(conn, user["id"], time_zone)
    return _start_session(request, conn, user["id"], _safe_next(next))


@router.post("/signout")
def signout(request: Request, conn: Conn):
    accounts.delete_session(conn, request.cookies.get(SESSION_COOKIE))
    response = RedirectResponse("/account/signin", status_code=303)
    response.delete_cookie(SESSION_COOKIE)
    return response
