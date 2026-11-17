import pytest

from shortener.urls import UrlError, validate_target_url

SERVICE_HOST = "short.test"


@pytest.mark.parametrize("url", ["https://example.com/a?x=1", "http://example.com"])
def test_accepts_http_and_https(url):
    assert validate_target_url(url, SERVICE_HOST) == url


def test_strips_surrounding_whitespace():
    assert validate_target_url("  https://example.com  ", SERVICE_HOST) == "https://example.com"


@pytest.mark.parametrize(
    ("url", "message"),
    [
        ("", "Enter the web address you want to shorten."),
        ("ftp://x", "starting with http:// or https://"),
        ("example.com", "starting with http:// or https://"),
        ("http://", "starting with http:// or https://"),
        ("http://[::1", "starting with http:// or https://"),
        ("https://example.com/" + "a" * 2030, "longer than 2,048 characters"),
        ("http://short.test/abcdefg", "already a short link"),
        ("https://SHORT.test/abcdefg", "already a short link"),
    ],
)
def test_rejects_with_specific_message(url, message):
    with pytest.raises(UrlError, match=message):
        validate_target_url(url, SERVICE_HOST)


def test_accepts_exactly_2048_characters():
    url = "https://example.com/" + "a" * (2048 - len("https://example.com/"))

    assert validate_target_url(url, SERVICE_HOST) == url
