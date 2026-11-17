import pytest
from playwright.sync_api import expect

LONG_URL = "https://example.com/a/very/long/path"


def shorten_through_form(page, base_url):
    page.goto(f"{base_url}/")
    page.get_by_label("Long web address").fill(LONG_URL)
    page.get_by_role("button", name="Shorten").click()
    page.wait_for_url(f"{base_url}/links/*")


@pytest.mark.browser
def test_copy_button_copies_the_short_link(signed_in_page, live_server):
    page = signed_in_page
    page.context.grant_permissions(["clipboard-read", "clipboard-write"], origin=live_server.url)
    page.clock.install()
    shorten_through_form(page, live_server.url)
    page.clock.pause_at(page.evaluate("Date.now()") + 1000)
    short_link = page.get_by_label("Short link").input_value()
    # Located by attribute, not by name: the name changes from "Copy" to "Copied".
    button = page.locator("[data-copy-target=short-link]")
    expect(button).to_have_text("Copy")

    button.click()

    expect(button).to_have_text("Copied")
    expect(page.locator("[aria-live=polite]")).to_contain_text("Copied")
    assert page.evaluate("navigator.clipboard.readText()") == short_link
    page.clock.fast_forward(2000)
    expect(button).to_have_text("Copy")


@pytest.mark.browser
def test_copy_falls_back_to_selecting_the_text(signed_in_page, live_server):
    page = signed_in_page
    page.add_init_script(
        "navigator.clipboard.writeText = () => Promise.reject(new Error('blocked'));"
    )
    shorten_through_form(page, live_server.url)

    page.get_by_role("button", name="Copy").click()

    expect(page.locator("[aria-live=polite]")).to_contain_text("Press Ctrl+C to copy")
    selection = page.evaluate(
        """() => {
            const el = document.activeElement;
            return [el.id, el.selectionStart, el.selectionEnd, el.value.length];
        }"""
    )
    assert selection[0] == "short-link"
    assert selection[1] == 0
    assert selection[2] == selection[3]
