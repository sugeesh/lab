from fastapi.testclient import TestClient

from tests.conftest import BASE_URL, PASSWORD, sign_up


def sign_in(client, email, password=PASSWORD, time_zone="UTC", next_path=""):
    return client.post(
        "/account/signin",
        data={"email": email, "password": password, "time_zone": time_zone, "next": next_path},
        follow_redirects=False,
    )


def test_signup_sets_a_safe_session_cookie(client):
    response = sign_up(client, "alice@example.com")

    assert response.status_code == 303
    assert response.headers["location"] == "/"
    cookie = response.headers["set-cookie"].lower()
    assert "session=" in cookie
    assert "httponly" in cookie
    assert "samesite=lax" in cookie


def test_signup_with_bad_input_shows_specific_message(client):
    response = sign_up(client, "alice@example.com", password="short")

    assert response.status_code == 400
    assert "Use a password with at least 8 characters." in response.text


def test_signup_with_taken_email(client, app):
    sign_up(client, "alice@example.com")

    response = sign_up(TestClient(app, base_url=BASE_URL), "alice@example.com")

    assert response.status_code == 400
    assert "already has an account" in response.text


def test_signin_redirects_to_next_and_updates_time_zone(client, app, conn):
    sign_up(client, "alice@example.com", time_zone="UTC")
    fresh = TestClient(app, base_url=BASE_URL)

    response = sign_in(fresh, "alice@example.com", time_zone="Asia/Colombo", next_path="/x/y")

    assert response.status_code == 303
    assert response.headers["location"] == "/x/y"
    row = conn.execute("SELECT time_zone FROM users").fetchone()
    assert row["time_zone"] == "Asia/Colombo"


def test_signin_defaults_to_home(client, app):
    sign_up(client, "alice@example.com")

    response = sign_in(TestClient(app, base_url=BASE_URL), "alice@example.com")

    assert response.headers["location"] == "/"


def test_signin_ignores_offsite_next(client, app):
    sign_up(client, "alice@example.com")

    response = sign_in(
        TestClient(app, base_url=BASE_URL), "alice@example.com", next_path="https://evil.test/"
    )

    assert response.headers["location"] == "/"


def test_signin_with_wrong_password(client, app):
    sign_up(client, "alice@example.com")

    response = sign_in(TestClient(app, base_url=BASE_URL), "alice@example.com", "wrong-pass")

    assert response.status_code == 400
    assert "Email or password is incorrect" in response.text


def test_signout_ends_the_session(signed_in_client):
    old_cookie = signed_in_client.cookies.get("session")

    response = signed_in_client.post("/account/signout", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/account/signin"
    signed_in_client.cookies.set("session", old_cookie)
    home = signed_in_client.get("/", follow_redirects=False)
    assert home.status_code == 303


def test_home_requires_sign_in(client):
    response = client.get("/", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/account/signin?next=/"


def test_signin_page_renders(client):
    assert client.get("/account/signin").status_code == 200
    assert client.get("/account/signup").status_code == 200
