"""Constitution III: people always get a plain-language page, never JSON or a bare error."""

import html
import logging

import pytest
from fastapi.testclient import TestClient

from shortener import codes, links
from tests.conftest import BASE_URL
from tests.integration.test_us1_shorten import link_count, shorten


def assert_html(response):
    assert response.headers["content-type"].startswith("text/html")
    assert "{" not in response.text.split("<main>")[1][:20]


@pytest.mark.parametrize("path", ["/links/abc/xyz", "/account/nope", "/static/missing.css"])
def test_unknown_paths_show_the_not_found_page(client, path):
    response = client.get(path)

    assert response.status_code == 404
    assert_html(response)
    assert "Link not found" in response.text


def test_wrong_method_shows_a_plain_page(client):
    response = client.put("/")

    assert response.status_code == 405
    assert_html(response)
    assert "This page can't be used that way." in html.unescape(response.text)


def test_no_free_code_asks_to_try_again(signed_in_client, conn, monkeypatch):
    def exhausted(*args, **kwargs):
        raise codes.CodeExhaustedError("no free code")

    monkeypatch.setattr(codes, "issue_code", exhausted)

    response = shorten(signed_in_client)

    assert response.status_code == 503
    assert "We couldn't create a short link just now. Please try again." in html.unescape(
        response.text
    )
    assert link_count(conn) == 0


def test_unexpected_error_shows_a_plain_page_and_is_logged(
    app, signed_in_client, monkeypatch, caplog
):
    def broken(*args, **kwargs):
        raise RuntimeError("database file is corrupt")

    monkeypatch.setattr(links, "list_links", broken)
    client = TestClient(app, base_url=BASE_URL, raise_server_exceptions=False)
    client.cookies = signed_in_client.cookies

    with caplog.at_level(logging.ERROR):
        response = client.get("/")

    assert response.status_code == 500
    assert_html(response)
    assert "problem on our side" in response.text
    assert "database file is corrupt" not in response.text
    logged = [r.exc_info[1] for r in caplog.records if r.levelno == logging.ERROR and r.exc_info]
    assert any("database file is corrupt" in str(error) for error in logged)
