from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from finsent.app.config.settings import settings


Base = declarative_base()

if settings.database_url.startswith("sqlite:///"):
    sqlite_path = Path(settings.database_url.replace("sqlite:///", "", 1))
    sqlite_path.parent.mkdir(parents=True, exist_ok=True)

engine = create_engine(settings.database_url, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def init_db() -> None:
    from finsent.app.database import entities  # noqa: F401

    Base.metadata.create_all(bind=engine)
