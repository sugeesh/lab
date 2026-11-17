import socket
import threading
import time
from types import SimpleNamespace

import pytest
import uvicorn

from shortener import db
from shortener.main import create_app

PASSWORD = "password123"


def _free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@pytest.fixture
def live_server(tmp_path):
    port = _free_port()
    url = f"http://127.0.0.1:{port}"
    db_path = str(tmp_path / "browser.db")
    app = create_app(db_path=db_path, base_url=url)
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    while not server.started:
        time.sleep(0.01)
    yield SimpleNamespace(url=url, db_path=db_path)
    server.should_exit = True
    thread.join()


@pytest.fixture
def live_db(live_server):
    connection = db.connect(live_server.db_path)
    yield connection
    connection.close()


def sign_up_through_form(page, base_url, email):
    page.goto(f"{base_url}/account/signup")
    page.get_by_label("Email").fill(email)
    page.get_by_label("Password").fill(PASSWORD)
    page.get_by_role("button", name="Create account").click()
    page.wait_for_url(f"{base_url}/")


@pytest.fixture
def signed_in_page(page, live_server):
    sign_up_through_form(page, live_server.url, "carol@example.com")
    return page
