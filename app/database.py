from __future__ import annotations

import os
import sqlite3
from datetime import datetime
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import settings


REQUIRED_SQLITE_COLUMNS = {
    "support_sessions": {
        "session_id",
        "platform_id",
        "channel",
        "channel_user_id",
        "platform_user_id",
        "locale",
        "last_route",
        "turns_count",
        "clarification_turns",
        "created_at",
        "updated_at",
    },
    "message_events": {
        "id",
        "message_id",
        "session_id",
        "direction",
        "route",
        "text",
        "payload_json",
        "created_at",
    },
    "handoff_summaries": {
        "id",
        "case_id",
        "session_id",
        "message_id",
        "route",
        "summary_type",
        "user_id",
        "current_status",
        "missing_items_json",
        "rejection_reason",
        "suggested_action",
        "payload_json",
        "created_at",
    },
    "review_cases": {
        "id",
        "case_id",
        "session_id",
        "message_id",
        "route",
        "decision",
        "confidence",
        "payload_json",
        "created_at",
    },
}


def get_sqlite_path(database_url: str) -> Path | None:
    if not database_url.startswith("sqlite:///"):
        return None
    return Path(database_url.replace("sqlite:///", "", 1))


def _table_columns(connection: sqlite3.Connection, table_name: str) -> set[str]:
    rows = connection.execute(f"PRAGMA table_info({table_name})").fetchall()
    return {row[1] for row in rows}


def sqlite_schema_is_compatible(sqlite_path: Path) -> bool:
    if not sqlite_path.exists():
        return True
    connection = sqlite3.connect(sqlite_path)
    try:
        for table_name, required_columns in REQUIRED_SQLITE_COLUMNS.items():
            existing_columns = _table_columns(connection, table_name)
            if existing_columns and not required_columns.issubset(existing_columns):
                return False
        return True
    finally:
        connection.close()


def reset_incompatible_sqlite_schema(database_url: str) -> Path | None:
    sqlite_path = get_sqlite_path(database_url)
    if sqlite_path is None or not sqlite_path.exists():
        return None
    if sqlite_schema_is_compatible(sqlite_path):
        return None
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    backup_path = sqlite_path.with_name(f"{sqlite_path.stem}.backup-{timestamp}{sqlite_path.suffix}")
    sqlite_path.replace(backup_path)
    return backup_path


sqlite_path = get_sqlite_path(settings.database_url)
if sqlite_path is not None:
    directory = os.path.dirname(str(sqlite_path))
    if directory:
        os.makedirs(directory, exist_ok=True)

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, future=True, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
