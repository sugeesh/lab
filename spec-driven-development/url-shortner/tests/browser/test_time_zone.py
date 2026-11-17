import pytest
from playwright.sync_api import expect

from tests.browser.conftest import sign_up_through_form


@pytest.mark.browser
def test_browser_time_zone_is_sent_and_saved_on_signup(browser, live_server, live_db):
    context = browser.new_context(timezone_id="Asia/Colombo")
    page = context.new_page()

    page.goto(f"{live_server.url}/account/signup")
    expect(page.locator("input[name=time_zone]")).to_have_value("Asia/Colombo")

    sign_up_through_form(page, live_server.url, "dave@example.com")

    row = live_db.execute("SELECT time_zone FROM users WHERE email = ?", ("dave@example.com",))
    assert row.fetchone()["time_zone"] == "Asia/Colombo"
    context.close()
