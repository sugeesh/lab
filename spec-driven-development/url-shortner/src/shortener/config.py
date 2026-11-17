import os
from dataclasses import dataclass
from urllib.parse import urlsplit


@dataclass(frozen=True)
class Settings:
    db_path: str
    base_url: str

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            db_path=os.environ.get("SHORTENER_DB", "./shortener.db"),
            base_url=os.environ.get("SHORTENER_BASE_URL", "http://localhost:8000").rstrip("/"),
        )

    @property
    def host(self) -> str:
        return urlsplit(self.base_url).hostname or ""

    @property
    def secure_cookies(self) -> bool:
        return urlsplit(self.base_url).scheme == "https"
