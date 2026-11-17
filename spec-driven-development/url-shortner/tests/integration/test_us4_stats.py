import logging
import re
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient

from shortener import clicks
from tests.conftest import BASE_URL, PASSWORD, sign_up
from tests.integration.test_us1_shorten import code_from, shorten
from tests.integration.test_us3_expiry import expire_now

ROW = re.compile(r'data-day="(\d{4}-\d{2}-\d{2})".*?<td class="number">(\d+)</td>', re.S)


def today_in(zone):
    return datetime.now(UTC).astimezone(ZoneInfo(zone)).date()


def visit(app, code, times=1):
    visitor = TestClient(app, base_url=BASE_URL)
    return [visitor.get(f"/{code}", follow_redirects=False) for _ in range(times)]


def stored_days(conn, code):
    rows = conn.execute("SELECT day, count FROM daily_clicks WHERE code = ? ORDER BY day", (code,))
    return [tuple(row) for row in rows]


def test_stats_show_total_and_last_30_days(signed_in_client, app, conn):
    conn.execute("UPDATE users SET time_zone = 'Asia/Colombo'")
    code = code_from(shorten(signed_in_client))
    today = today_in("Asia/Colombo")
    yesterday = today - timedelta(days=1)
    conn.execute(
        "INSERT INTO daily_clicks (code, day, count) VALUES (?, ?, 3)",
        (code, yesterday.isoformat()),
    )

    assert all(r.status_code == 302 for r in visit(app, code, times=5))

    page = signed_in_client.get(f"/links/{code}").text
    days = dict(ROW.findall(page))
    assert len(days) == 30
    assert days[today.isoformat()] == "5"
    assert days[yesterday.isoformat()] == "3"
    assert sum(int(count) for count in days.values()) == 8
    assert re.search(r"Total clicks</dt>\s*<dd>8</dd>", page)
    assert "Days shown in Asia/Colombo" in page
    assert re.search(r'data-label="Clicks" class="number">8<', signed_in_client.get("/").text)


def test_visits_that_do_not_redirect_are_not_counted(signed_in_client, app, conn):
    disabled = code_from(shorten(signed_in_client))
    signed_in_client.post(f"/links/{disabled}/disable")
    expired = code_from(shorten(signed_in_client))
    expire_now(conn, expired)

    visit(app, disabled)
    visit(app, expired)
    visit(app, "ZZZZZZZ")

    assert conn.execute("SELECT COUNT(*) FROM daily_clicks").fetchone()[0] == 0


def test_deleting_a_link_removes_its_clicks(signed_in_client, app, conn):
    code = code_from(shorten(signed_in_client))
    visit(app, code, times=2)
    assert stored_days(conn, code) != []

    signed_in_client.post(f"/links/{code}/delete")

    assert stored_days(conn, code) == []


def test_failed_click_recording_still_redirects_and_is_logged(
    signed_in_client, app, monkeypatch, caplog
):
    code = code_from(shorten(signed_in_client))

    def broken(*args, **kwargs):
        raise RuntimeError("disk full")

    monkeypatch.setattr(clicks, "record_click", broken)

    with caplog.at_level(logging.ERROR):
        [response] = visit(app, code)

    assert response.status_code == 302
    errors = [r for r in caplog.records if r.levelno == logging.ERROR]
    assert any(code in r.getMessage() for r in errors)


def test_clicks_follow_the_time_zone_saved_at_latest_sign_in(app, conn):
    # 25 hours apart, so "today" is always a different date in these two zones.
    owner = TestClient(app, base_url=BASE_URL)
    sign_up(owner, "pat@example.com", time_zone="Pacific/Pago_Pago")
    code = code_from(shorten(owner))
    fresh = TestClient(app, base_url=BASE_URL)
    fresh.post(
        "/account/signin",
        data={"email": "pat@example.com", "password": PASSWORD, "time_zone": "Pacific/Kiritimati"},
    )

    visit(app, code)

    assert stored_days(conn, code) == [(today_in("Pacific/Kiritimati").isoformat(), 1)]
