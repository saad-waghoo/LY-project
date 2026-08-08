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


def _apply_sqlite_migrations() -> None:
    if not settings.database_url.startswith("sqlite:///"):
        return

    required_columns = {
        "news_articles": {
            "exchange": "VARCHAR(16)",
            "provider": "VARCHAR(64)",
            "ingested_at": "DATETIME",
            "dedupe_hash": "VARCHAR(128)",
            "relevance_score": "FLOAT",
            "model_label": "VARCHAR(32)",
            "model_confidence": "FLOAT",
            "text_score": "FLOAT",
            "signal_confidence": "FLOAT",
            "bid_ask_spread": "FLOAT",
            "spread_pct": "FLOAT",
            "volume_ratio": "FLOAT",
            "buy_sell_ratio": "FLOAT",
            "buy_pressure": "FLOAT",
            "market_signal": "FLOAT",
            "relevant": "INTEGER",
            "impact_strength": "FLOAT",
            "time_horizon": "VARCHAR(32)",
            "catalyst_tag": "VARCHAR(64)",
            "short_reason": "TEXT",
            "analysis_provider": "VARCHAR(64)",
            "parse_status": "VARCHAR(32)",
        }
    }

    with engine.begin() as connection:
        tables = {
            row[0]
            for row in connection.exec_driver_sql(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        for table_name, columns in required_columns.items():
            if table_name not in tables:
                continue
            existing = {
                row[1]
                for row in connection.exec_driver_sql(f"PRAGMA table_info({table_name})").fetchall()
            }
            for column_name, column_type in columns.items():
                if column_name in existing:
                    continue
                connection.exec_driver_sql(
                    f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"
                )


def init_db() -> None:
    from finsent.app.database import entities  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _apply_sqlite_migrations()
