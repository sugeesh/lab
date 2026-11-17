import re
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from shortener import db
from tests.conftest import BASE_URL, PASSWORD

LONG_URL = "https://example.com/a/very/long/path?x=1"


def shorten(client, url=LONG_URL):
    return client.post("/links", data={"url": url}, follow_redirects=False)


def code_from(response):
    match = re.fullmatch(r"/links/([A-Za-z0-9]{7})", response.headers["location"])
    assert match, response.headers.get("location")
    return match.group(1)


def link_count(conn):
    return conn.execute("SELECT COUNT(*) FROM links").fetchone()[0]


def test_shortening_shows_the_short_link_with_copy_button(signed_in_client):
    response = shorten(signed_in_client)

    assert response.status_code == 303
    code = code_from(response)
    page = signed_in_client.get(response.headers["location"])
    assert page.status_code == 200
    assert f'value="{BASE_URL}/{code}"' in page.text
    assert ">Copy</button>" in page.text
    assert LONG_URL.replace("&", "&amp;") in page.text


def test_anyone_opening_the_short_link_is_redirected(signed_in_client, app):
    code = code_from(shorten(signed_in_client))
    visitor = TestClient(app, base_url=BASE_URL)

    response = visitor.get(f"/{code}", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["location"] == LONG_URL
    assert response.headers["cache-control"] == "no-store"


def test_invalid_addresses_are_refused_with_a_message(signed_in_client, conn):
    for url, message in [
        ("ftp://x", "starting with http:// or https://"),
        (f"{BASE_URL}/abcdefg", "already a short link"),
    ]:
        response = shorten(signed_in_client, url)

        assert response.status_code == 400
        assert message in response.text
        assert f'value="{url}"' in response.text
    assert link_count(conn) == 0


def test_signed_out_user_is_sent_to_sign_in_then_home(client, app):
    client.post(
        "/account/signup",
        data={"email": "alice@example.com", "password": PASSWORD, "time_zone": "UTC"},
    )
    visitor = TestClient(app, base_url=BASE_URL)

    response = shorten(visitor)

    assert response.status_code == 303
    assert response.headers["location"] == "/account/signin?next=/"
    signed_in = visitor.post(
        "/account/signin",
        data={"email": "alice@example.com", "password": PASSWORD, "next": "/"},
        follow_redirects=False,
    )
    assert signed_in.headers["location"] == "/"
    assert 'action="/links"' in visitor.get("/").text


def test_same_address_twice_gets_two_codes(signed_in_client):
    first = code_from(shorten(signed_in_client))
    second = code_from(shorten(signed_in_client))

    assert first != second


def test_unknown_code_shows_not_found_page(client):
    response = client.get("/ZZZZZZZ", follow_redirects=False)

    assert response.status_code == 404
    assert "Link not found" in response.text


def test_other_paths_show_not_found_page(client):
    for path in ["/abc", "/favicon.ico", "/abcdefgh"]:
        response = client.get(path, follow_redirects=False)

        assert response.status_code == 404
        assert "Link not found" in response.text


def test_hourly_limit_refuses_the_101st_link(signed_in_client, conn):
    user_id = conn.execute("SELECT id FROM users").fetchone()["id"]
    first_at = datetime.now(UTC) - timedelta(minutes=30)
    conn.executemany(
        "INSERT INTO issued_codes (code, user_id, issued_at) VALUES (?, ?, ?)",
        [(f"R{i:06d}", user_id, db.to_text(first_at + timedelta(seconds=i))) for i in range(100)],
    )

    response = shorten(signed_in_client)

    assert response.status_code == 429
    retry_at = (first_at + timedelta(minutes=60)).strftime("%H:%M")
    assert f"You've created 100 links in the last hour. You can create more at {retry_at}" in (
        response.text.replace("&#39;", "'")
    )
    assert link_count(conn) == 0


def test_codes_are_case_sensitive(signed_in_client, app, conn):
    user_id = conn.execute("SELECT id FROM users").fetchone()["id"]
    conn.execute(
        "INSERT INTO issued_codes (code, user_id, issued_at) VALUES ('AbCdEf1', ?, ?)",
        (user_id, "2026-11-17T12:00:00Z"),
    )
    conn.execute(
        "INSERT INTO links (code, user_id, target_url, created_at) VALUES ('AbCdEf1', ?, ?, ?)",
        (user_id, LONG_URL, "2026-11-17T12:00:00Z"),
    )
    visitor = TestClient(app, base_url=BASE_URL)

    assert visitor.get("/AbCdEf1", follow_redirects=False).status_code == 302
    assert visitor.get("/aBcDeF1", follow_redirects=False).status_code == 404


def test_link_page_is_private_to_its_owner(signed_in_client, other_client):
    code = code_from(shorten(signed_in_client))

    response = other_client.get(f"/links/{code}")

    assert response.status_code == 404
    assert "Link not found" in response.text
