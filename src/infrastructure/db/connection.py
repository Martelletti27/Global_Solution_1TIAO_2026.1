"""Conexao SQLite com row_factory habilitado."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from src.config import DB_PATH, ensure_data_dirs


def connect(db_path: Path | str | None = None) -> sqlite3.Connection:
    """Abre conexao com linhas acessiveis por nome de coluna."""
    if db_path is None:
        ensure_data_dirs()
        db_path = DB_PATH
    else:
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def db_session(db_path: Path | str | None = None) -> Iterator[sqlite3.Connection]:
    """Context manager que fecha a conexao ao final."""
    conn = connect(db_path)
    try:
        yield conn
    finally:
        conn.close()
