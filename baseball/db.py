"""Database connection and schema management.

Thin wrapper around ``sqlite3`` that applies the schema, enables foreign keys,
and returns rows as dictionaries so callers can use column names directly.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

# Default on-disk location for the database file.
DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "baseball.db"
SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"


def dict_factory(cursor: sqlite3.Cursor, row: tuple) -> dict:
    """Row factory that yields ``{column: value}`` dicts."""
    return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}


def connect(db_path: str | Path = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """Open a connection with foreign keys on and dict rows.

    Passing ``":memory:"`` gives an ephemeral in-memory database, which is what
    the tests use.
    """
    if db_path != ":memory:":
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = dict_factory
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    """Create all tables, indexes, and views from ``schema.sql``."""
    conn.executescript(SCHEMA_PATH.read_text())
    conn.commit()
