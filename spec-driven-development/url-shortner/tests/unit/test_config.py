from shortener.config import Settings


def test_defaults_when_env_is_empty(monkeypatch):
    monkeypatch.delenv("SHORTENER_DB", raising=False)
    monkeypatch.delenv("SHORTENER_BASE_URL", raising=False)

    settings = Settings.from_env()

    assert settings.db_path == "./shortener.db"
    assert settings.base_url == "http://localhost:8000"


def test_reads_values_from_env(monkeypatch):
    monkeypatch.setenv("SHORTENER_DB", "/tmp/links.db")
    monkeypatch.setenv("SHORTENER_BASE_URL", "https://sho.rt")

    settings = Settings.from_env()

    assert settings.db_path == "/tmp/links.db"
    assert settings.base_url == "https://sho.rt"


def test_host_is_taken_from_base_url():
    assert Settings(db_path="x", base_url="https://sho.rt:8443").host == "sho.rt"


def test_secure_cookies_only_for_https():
    assert Settings(db_path="x", base_url="https://sho.rt").secure_cookies is True
    assert Settings(db_path="x", base_url="http://localhost:8000").secure_cookies is False
