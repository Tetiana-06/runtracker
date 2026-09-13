"""Ініціалізація SQLAlchemy: engine, сесії та базовий клас моделей."""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

connect_args = {"check_same_thread": False} if settings.is_sqlite else {}

engine = create_engine(settings.database_url, connect_args=connect_args, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    """Базовий клас для всіх ORM-моделей."""


def get_db() -> Generator[Session, None, None]:
    """Залежність FastAPI: віддає сесію і гарантовано закриває її."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Створює таблиці, якщо їх ще немає."""
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
