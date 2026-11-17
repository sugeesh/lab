from fastapi.testclient import TestClient

from tests.conftest import BASE_URL
from tests.integration.test_us1_shorten import code_from, shorten


def visit(app, code):
    return TestClient(app, base_url=BASE_URL).get(f"/{code}", follow_redirects=False)


def test_list_shows_only_my_links_newest_first(signed_in_client, other_client):
    codes = [code_from(shorten(signed_in_client, f"https://example.com/{n}")) for n in range(3)]
    others = code_from(shorten(other_client, "https://example.org/bob"))

    page = signed_in_client.get("/").text

    positions = [page.index(f"{BASE_URL}/{code}") for code in reversed(codes)]
    assert positions == sorted(positions)
    assert others not in page
    for n in range(3):
        assert f"https://example.com/{n}" in page
    assert page.count("Active") == 3
    assert page.count("No expiry") == 3
    assert "Clicks" in page


def test_empty_list(signed_in_client):
    assert "No links yet" in signed_in_client.get("/").text


def test_disable_and_enable(signed_in_client, app):
    code = code_from(shorten(signed_in_client))

    response = signed_in_client.post(f"/links/{code}/disable", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == f"/links/{code}"
    disabled = visit(app, code)
    assert disabled.status_code == 403
    assert "This link is disabled" in disabled.text
    assert "Disabled" in signed_in_client.get(f"/links/{code}").text
    assert "Disabled" in signed_in_client.get("/").text

    signed_in_client.post(f"/links/{code}/enable", follow_redirects=False)

    assert visit(app, code).status_code == 302


def test_delete_after_confirmation(signed_in_client, app, conn):
    code = code_from(shorten(signed_in_client))

    confirm = signed_in_client.get(f"/links/{code}/delete")
    assert confirm.status_code == 200
    assert "never be used again" in confirm.text
    assert 'action="/links/' + code + '/delete"' in confirm.text

    response = signed_in_client.post(f"/links/{code}/delete", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/"
    assert code not in signed_in_client.get("/").text
    assert visit(app, code).status_code == 404
    issued = conn.execute("SELECT 1 FROM issued_codes WHERE code = ?", (code,)).fetchone()
    assert issued is not None


def test_other_users_cannot_see_or_change_my_link(signed_in_client, other_client, app):
    code = code_from(shorten(signed_in_client))

    assert other_client.get(f"/links/{code}").status_code == 404
    assert other_client.get(f"/links/{code}/delete").status_code == 404
    for action in ["disable", "enable", "expiry", "delete"]:
        response = other_client.post(f"/links/{code}/{action}", follow_redirects=False)
        assert response.status_code == 404, action

    assert visit(app, code).status_code == 302
    assert signed_in_client.get(f"/links/{code}").status_code == 200
