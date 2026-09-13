"""Конфігурація застосунку.

Налаштування читаються зі змінних оточення, щоб один і той самий код
запускався локально (SQLite) і в Docker (PostgreSQL).
"""

import os


class Settings:
    """Прості налаштування без зовнішніх залежностей."""

    def __init__(self) -> None:
        self.app_name = "RunTracker API"
        self.version = "1.0.0"
        self.database_url = os.getenv("DATABASE_URL", "sqlite:///./runtracker.db")
        self.cors_origins = os.getenv("CORS_ORIGINS", "*").split(",")

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")


settings = Settings()
