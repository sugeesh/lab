from urllib.parse import urlsplit

MAX_URL_LENGTH = 2048


class UrlError(ValueError):
    pass


def validate_target_url(url: str, service_host: str) -> str:
    url = url.strip()
    if not url:
        raise UrlError("Enter the web address you want to shorten.")
    if len(url) > MAX_URL_LENGTH:
        raise UrlError("That address is longer than 2,048 characters. Use a shorter address.")
    try:
        parts = urlsplit(url)
        host = parts.hostname
    except ValueError:
        host = None
    if host is None or parts.scheme not in ("http", "https"):
        raise UrlError("Enter a full web address starting with http:// or https://.")
    if host == service_host.lower():
        raise UrlError(
            "That address is already a short link from this service. "
            "Enter the original address instead."
        )
    return url
