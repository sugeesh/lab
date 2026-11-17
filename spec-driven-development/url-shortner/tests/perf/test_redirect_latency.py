"""SC-001: with 1M links stored and 50 redirects/s sustained, p95 server time < 50 ms.

Run on demand: pytest -m perf -s
"""

import os
import random
import socket
import statistics
import subprocess
import sys
import time

import httpx
import pytest

from shortener import db
from shortener.codes import generate_code

LINK_COUNT = 1_000_000
RATE_PER_SECOND = 50
DURATION_SECONDS = 30
P95_LIMIT_MS = 50.0
CREATED = "2026-11-17T12:00:00Z"


def seed(db_path: str) -> list[str]:
    codes: set[str] = set()
    while len(codes) < LINK_COUNT:  # a set, so a random duplicate can never break the insert
        codes.add(generate_code())
    ordered = list(codes)
    conn = db.connect(db_path)
    db.init_schema(conn)
    with db.transaction(conn):
        conn.execute(
            "INSERT INTO users (id, email, password_hash, created_at) "
            "VALUES (1, 'load@example.com', 'x', ?)",
            (CREATED,),
        )
        conn.executemany(
            "INSERT INTO issued_codes (code, user_id, issued_at) VALUES (?, 1, ?)",
            ((code, CREATED) for code in ordered),
        )
        conn.executemany(
            "INSERT INTO links (code, user_id, target_url, created_at) VALUES (?, 1, ?, ?)",
            ((code, f"https://example.com/{code}", CREATED) for code in ordered),
        )
    conn.close()
    return ordered


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def start_server(db_path: str, port: int) -> subprocess.Popen:
    env = {
        **os.environ,
        "SHORTENER_DB": db_path,
        "SHORTENER_BASE_URL": f"http://127.0.0.1:{port}",
    }
    command = [sys.executable, "-m", "uvicorn", "shortener.main:create_app", "--factory"]
    command += ["--port", str(port), "--log-level", "warning"]
    server = subprocess.Popen(command, env=env)
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        try:
            httpx.get(f"http://127.0.0.1:{port}/account/signin")
            return server
        except httpx.TransportError:
            time.sleep(0.1)
    server.kill()
    raise RuntimeError("server did not start")


def server_ms(response: httpx.Response) -> float:
    return float(response.headers["server-timing"].split("dur=")[1])


@pytest.mark.perf
def test_redirect_p95_under_50ms_with_1m_links(tmp_path):
    db_path = str(tmp_path / "perf.db")
    codes = seed(db_path)
    port = free_port()
    server = start_server(db_path, port)
    durations, statuses = [], []
    try:
        with httpx.Client(base_url=f"http://127.0.0.1:{port}") as client:
            started = time.monotonic()
            for i in range(RATE_PER_SECOND * DURATION_SECONDS):
                wait = started + i / RATE_PER_SECOND - time.monotonic()
                if wait > 0:
                    time.sleep(wait)
                response = client.get(f"/{random.choice(codes)}", follow_redirects=False)
                statuses.append(response.status_code)
                durations.append(server_ms(response))
            elapsed = time.monotonic() - started
    finally:
        server.terminate()
        server.wait()

    p95 = statistics.quantiles(durations, n=100)[94]
    print(
        f"\n{len(durations)} redirects in {elapsed:.1f}s; server time "
        f"p50={statistics.median(durations):.2f}ms p95={p95:.2f}ms max={max(durations):.2f}ms"
    )
    assert set(statuses) == {302}
    assert p95 < P95_LIMIT_MS
