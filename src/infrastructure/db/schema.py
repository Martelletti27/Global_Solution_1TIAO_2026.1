"""DDL e inicializacao do schema SQLite."""

from __future__ import annotations

import sqlite3

SCHEMA_VERSION = 1

_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS schema_meta (
    version INTEGER NOT NULL,
    applied_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS grid_cells (
    region_key TEXT PRIMARY KEY,
    lat_center REAL NOT NULL,
    lon_center REAL NOT NULL,
    state TEXT,
    row_idx INTEGER NOT NULL,
    col_idx INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS fire_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    acq_date TEXT NOT NULL,
    acq_time TEXT,
    brightness REAL,
    confidence TEXT,
    frp REAL,
    satellite TEXT,
    instrument TEXT,
    region_key TEXT,
    dedup_key TEXT NOT NULL UNIQUE,
    ingested_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (region_key) REFERENCES grid_cells(region_key)
);

CREATE INDEX IF NOT EXISTS idx_fire_events_date
    ON fire_events(acq_date);
CREATE INDEX IF NOT EXISTS idx_fire_events_region
    ON fire_events(region_key);
CREATE INDEX IF NOT EXISTS idx_fire_events_region_date
    ON fire_events(region_key, acq_date);

CREATE TABLE IF NOT EXISTS weather_daily (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    region_key TEXT NOT NULL,
    weather_date TEXT NOT NULL,
    tmax_c REAL,
    tmin_c REAL,
    precip_mm REAL,
    wind_max_kmh REAL,
    pressure_hpa REAL,
    source TEXT,
    ingested_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(region_key, weather_date),
    FOREIGN KEY (region_key) REFERENCES grid_cells(region_key)
);

CREATE INDEX IF NOT EXISTS idx_weather_region_date
    ON weather_daily(region_key, weather_date);

CREATE TABLE IF NOT EXISTS risk_scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    region_key TEXT NOT NULL,
    reference_date TEXT NOT NULL,
    probability REAL NOT NULL,
    risk_score INTEGER NOT NULL,
    risk_level TEXT NOT NULL,
    priority_rank INTEGER,
    model_version TEXT,
    computed_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(region_key, reference_date),
    FOREIGN KEY (region_key) REFERENCES grid_cells(region_key)
);

CREATE INDEX IF NOT EXISTS idx_risk_reference
    ON risk_scores(reference_date);
CREATE INDEX IF NOT EXISTS idx_risk_level
    ON risk_scores(reference_date, risk_level);
CREATE INDEX IF NOT EXISTS idx_risk_rank
    ON risk_scores(reference_date, priority_rank);
"""


def init_db(conn: sqlite3.Connection) -> None:
    """Cria tabelas e indices se ainda nao existirem."""
    conn.executescript(_TABLES_SQL)
    _ensure_schema_version(conn)
    conn.commit()


def _ensure_schema_version(conn: sqlite3.Connection) -> None:
    """Registra versao do schema na primeira inicializacao."""
    row = conn.execute("SELECT COUNT(*) AS n FROM schema_meta").fetchone()
    if row and row["n"] == 0:
        conn.execute(
            "INSERT INTO schema_meta (version) VALUES (?)",
            (SCHEMA_VERSION,),
        )


def get_schema_version(conn: sqlite3.Connection) -> int | None:
    """Retorna versao aplicada ou None se banco vazio."""
    row = conn.execute(
        "SELECT version FROM schema_meta ORDER BY applied_at DESC LIMIT 1"
    ).fetchone()
    if row is None:
        return None
    return int(row["version"])
