"""Constitution III: every page works at 320 px and the core flow works by keyboard alone."""

import pytest
from playwright.sync_api import expect

from tests.browser.test_copy_button import LONG_URL, shorten_through_form

PHONE_WIDTH = 320


def assert_fits(page, url):
    page.goto(url)
    scroll_width = page.evaluate("document.documentElement.scrollWidth")
    assert scroll_width <= PHONE_WIDTH, f"{url} is {scroll_width}px wide"


@pytest.mark.browser
def test_every_page_fits_a_phone_screen(signed_in_page, live_server):
    page = signed_in_page
    page.set_viewport_size({"width": PHONE_WIDTH, "height": 640})
    shorten_through_form(page, live_server.url)
    detail = page.url

    for url in [f"{live_server.url}/", detail, f"{detail}/delete", f"{live_server.url}/ZZZZZZZ"]:
        assert_fits(page, url)

    page.context.clear_cookies()
    for path in ["/account/signin", "/account/signup"]:
        assert_fits(page, f"{live_server.url}{path}")


@pytest.mark.browser
def test_shorten_and_copy_with_the_keyboard_only(signed_in_page, live_server):
    page = signed_in_page
    page.context.grant_permissions(["clipboard-read", "clipboard-write"], origin=live_server.url)
    page.goto(f"{live_server.url}/")

    page.keyboard.type(LONG_URL)  # the address field has focus on arrival
    page.keyboard.press("Enter")
    page.wait_for_url(f"{live_server.url}/links/*")

    for _ in range(10):
        page.keyboard.press("Tab")
        if page.evaluate("document.activeElement.dataset.copyTarget") == "short-link":
            break
    else:
        pytest.fail("Copy button is not reachable with Tab")
    page.keyboard.press("Enter")

    expect(page.locator("[aria-live=polite]")).to_contain_text("Copied")
