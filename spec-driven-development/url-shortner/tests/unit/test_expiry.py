from datetime import UTC, datetime

import pytest

from shortener.links import ExpiryError, parse_local_expiry

NOW = datetime(2026, 11, 17, 12, 0, tzinfo=UTC)


def test_empty_means_no_expiry():
    assert parse_local_expiry("", "UTC", NOW) is None
    assert parse_local_expiry("   ", "UTC", NOW) is None


def test_local_time_is_converted_to_utc():
    assert parse_local_expiry("2026-12-01T09:30", "Asia/Colombo", NOW) == "2026-12-01T04:00:00Z"


def test_seconds_from_the_browser_are_accepted():
    assert parse_local_expiry("2026-12-01T09:30:00", "UTC", NOW) == "2026-12-01T09:30:00Z"


@pytest.mark.parametrize("value", ["2026-11-17T12:00", "2026-11-17T11:59", "2020-01-01T00:00"])
def test_now_or_past_is_rejected(value):
    with pytest.raises(ExpiryError, match="Choose a time in the future."):
        parse_local_expiry(value, "UTC", NOW)


@pytest.mark.parametrize("value", ["tomorrow", "2026-13-01T00:00", "2026-12-01"])
def test_malformed_is_rejected_with_a_plain_message(value):
    with pytest.raises(ExpiryError, match="Enter the expiry as a date and a time."):
        parse_local_expiry(value, "UTC", NOW)


def test_a_time_beyond_year_9999_in_utc_is_rejected_with_a_message():
    # 23:59 on 31 Dec 9999 in UTC-11 is already year 10000 in UTC.
    with pytest.raises(ExpiryError, match="Choose a date before the year 9999."):
        parse_local_expiry("9999-12-31T23:59", "Pacific/Pago_Pago", NOW)


@pytest.mark.parametrize("zone", ["UTC", "Pacific/Kiritimati"])
def test_any_year_9999_date_is_rejected(zone):
    with pytest.raises(ExpiryError, match="Choose a date before the year 9999."):
        parse_local_expiry("9999-06-01T00:00", zone, NOW)


def test_last_day_of_9998_is_accepted_even_far_behind_utc():
    assert parse_local_expiry("9998-12-31T23:59", "Pacific/Pago_Pago", NOW) == (
        "9999-01-01T10:59:00Z"
    )
