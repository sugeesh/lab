import pytest
from fastapi.testclient import TestClient

from shortener import db
from shortener.main import create_app

BASE_URL = "http://short.test"
PASSWORD = "password123"


def sign_up(client, email, password=PASSWORD, time_zone="UTC"):
    return client.post(
        "/account/signup",
        data={"email": email, "password": password, "time_zone": time_zone},
        follow_redirects=False,
    )


@pytest.fixture
def db_path(tmp_path):
    return str(tmp_path / "test.db")


@pytest.fixture
def app(db_path):
    return create_app(db_path=db_path, base_url=BASE_URL)


@pytest.fixture
def client(app):
    return TestClient(app, base_url=BASE_URL)


@pytest.fixture
def signed_in_client(client):
    response = sign_up(client, "alice@example.com")
    assert response.status_code == 303
    return client


@pytest.fixture
def other_client(app):
    other = TestClient(app, base_url=BASE_URL)
    response = sign_up(other, "bob@example.com")
    assert response.status_code == 303
    return other


@pytest.fixture
def conn(app, db_path):
    connection = db.connect(db_path)
    yield connection
    connection.close()
