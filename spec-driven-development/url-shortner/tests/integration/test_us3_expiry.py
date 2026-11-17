from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from tests.conftest import BASE_URL
from tests.integration.test_us1_shorten import LONG_URL, code_from, link_count, shorten

PAST_TEXT = "2020-01-01T00:00:00Z"


def local_input(delta: timedelta) -> str:
    return (datetime.now(UTC) + delta).strftime("%Y-%m-%dT%H:%M")


def visit(app, code):
    return TestClient(app, base_url=BASE_URL).get(f"/{code}", follow_redirects=False)


def shorten_with_expiry(client, expires_at):
    return client.post(
        "/links", data={"url": LONG_URL, "expires_at": expires_at}, follow_redirects=False
    )


def expire_now(conn, code):
    conn.execute("UPDATE links SET expires_at = ? WHERE code = ?", (PAST_TEXT, code))


def set_expiry(client, code, value):
    return client.post(f"/links/{code}/expiry", data={"expires_at": value}, follow_redirects=False)


def test_future_expiry_still_redirects(signed_in_client, app, conn):
    code = code_from(shorten_with_expiry(signed_in_client, local_input(timedelta(days=1))))

    assert visit(app, code).status_code == 302
    stored = conn.execute("SELECT expires_at FROM links WHERE code = ?", (code,)).fetchone()
    assert stored["expires_at"] is not None


def test_expired_link_shows_expired_page(signed_in_client, app, conn):
    code = code_from(shorten(signed_in_client))
    expire_now(conn, code)

    response = visit(app, code)

    assert response.status_code == 410
    assert "This link has expired" in response.text
    assert "01 Jan 2020" in response.text
    assert "location" not in response.headers


def test_past_expiry_is_refused_on_create(signed_in_client, conn):
    response = shorten_with_expiry(signed_in_client, local_input(-timedelta(hours=1)))

    assert response.status_code == 400
    assert "Choose a time in the future." in response.text
    assert link_count(conn) == 0


def test_past_expiry_is_refused_on_change(signed_in_client, conn):
    code = code_from(shorten(signed_in_client))

    response = set_expiry(signed_in_client, code, local_input(-timedelta(hours=1)))

    assert response.status_code == 400
    assert "Choose a time in the future." in response.text
    stored = conn.execute("SELECT expires_at FROM links WHERE code = ?", (code,)).fetchone()
    assert stored["expires_at"] is None


def test_new_future_expiry_brings_an_expired_link_back(signed_in_client, app, conn):
    code = code_from(shorten(signed_in_client))
    expire_now(conn, code)

    response = set_expiry(signed_in_client, code, local_input(timedelta(days=2)))

    assert response.status_code == 303
    assert response.headers["location"] == f"/links/{code}"
    assert visit(app, code).status_code == 302


def test_removing_expiry_brings_an_expired_link_back(signed_in_client, app, conn):
    code = code_from(shorten(signed_in_client))
    expire_now(conn, code)

    set_expiry(signed_in_client, code, "")

    assert visit(app, code).status_code == 302


def test_disabled_wins_over_expired(signed_in_client, app, conn):
    code = code_from(shorten(signed_in_client))
    expire_now(conn, code)
    signed_in_client.post(f"/links/{code}/disable")

    response = visit(app, code)

    assert response.status_code == 403
    assert "This link is disabled" in response.text


def test_expiry_shown_in_owner_time_zone(signed_in_client, conn):
    code = code_from(shorten(signed_in_client))
    conn.execute("UPDATE users SET time_zone = 'Asia/Colombo'")
    conn.execute("UPDATE links SET expires_at = '2099-12-01T04:00:00Z' WHERE code = ?", (code,))

    detail = signed_in_client.get(f"/links/{code}").text
    listing = signed_in_client.get("/").text

    assert "01 Dec 2099, 09:30" in detail
    assert "Asia/Colombo" in detail
    assert 'value="2099-12-01T09:30"' in detail
    assert "01 Dec 2099, 09:30" in listing

    expire_now(conn, code)
    assert "Expired" in signed_in_client.get(f"/links/{code}").text
    assert "Expired" in signed_in_client.get("/").text


def test_expiry_beyond_year_9999_is_refused_with_a_message(signed_in_client, conn):
    code = code_from(shorten(signed_in_client))
    conn.execute("UPDATE users SET time_zone = 'Pacific/Pago_Pago'")

    response = set_expiry(signed_in_client, code, "9999-12-31T23:59")

    assert response.status_code == 400
    assert "Choose a date before the year 9999." in response.text
    stored = conn.execute("SELECT expires_at FROM links WHERE code = ?", (code,)).fetchone()
    assert stored["expires_at"] is None


def test_pages_still_load_when_a_stored_expiry_cannot_be_shown_locally(signed_in_client, app, conn):
    code = code_from(shorten(signed_in_client))
    conn.execute("UPDATE links SET expires_at = '9999-12-31T23:59:00Z' WHERE code = ?", (code,))
    owner = TestClient(app, base_url=BASE_URL)
    owner.post(
        "/account/signin",
        data={
            "email": "alice@example.com",
            "password": "password123",
            "time_zone": "Pacific/Kiritimati",
        },
    )

    home = owner.get("/")
    detail = owner.get(f"/links/{code}")

    assert home.status_code == 200
    assert detail.status_code == 200
    assert "31 Dec 9999, 23:59 (UTC)" in detail.text
    assert "31 Dec 9999, 23:59 (UTC)" in home.text
