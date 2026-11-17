from datetime import UTC, datetime

import pytest

from shortener.links import status

NOW = datetime(2026, 11, 17, 12, 0, tzinfo=UTC)
PAST = "2026-11-17T11:59:59Z"
EXACTLY_NOW = "2026-11-17T12:00:00Z"
FUTURE = "2026-11-17T12:00:01Z"


@pytest.mark.parametrize(
    ("enabled", "expires_at", "expected"),
    [
        (1, None, "active"),
        (1, FUTURE, "active"),
        (1, EXACTLY_NOW, "expired"),
        (1, PAST, "expired"),
        (0, None, "disabled"),
        (0, PAST, "disabled"),
    ],
)
def test_status(enabled, expires_at, expected):
    assert status(enabled, expires_at, NOW) == expected
