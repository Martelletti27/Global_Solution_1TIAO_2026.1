"""CRUD basico para as tabelas do OrbitFire."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

from src.infrastructure.db.connection import db_session
from src.infrastructure.db.schema import init_db


@dataclass(frozen=True)
class GridCell:
    """Celula da grade geografica do Centro-Oeste."""

    region_key: str
    lat_center: float
    lon_center: float
    row_idx: int
    col_idx: int
    state: str | None = None


@dataclass(frozen=True)
class FireEvent:
    """Foco de calor detectado por satelite (FIRMS)."""

    latitude: float
    longitude: float
    acq_date: str
    dedup_key: str
    acq_time: str | None = None
    brightness: float | None = None
    confidence: str | None = None
    frp: float | None = None
    satellite: str | None = None
    instrument: str | None = None
    region_key: str | None = None


@dataclass(frozen=True)
class WeatherDaily:
    """Clima diario agregado por celula."""

    region_key: str
    weather_date: str
    tmax_c: float | None = None
    tmin_c: float | None = None
    precip_mm: float | None = None
    wind_max_kmh: float | None = None
    pressure_hpa: float | None = None
    source: str | None = None


@dataclass(frozen=True)
class RiskScore:
    """Score preditivo de risco de incendio para o dia seguinte."""

    region_key: str
    reference_date: str
    probability: float
    risk_score: int
    risk_level: str
    priority_rank: int | None = None
    model_version: str | None = None


class OrbitFireRepository:
    """Repositorio SQLite com operacoes de leitura e escrita."""

    def __init__(self, db_path: Path | str | None = None) -> None:
        self._db_path = db_path

    def initialize(self) -> None:
        """Cria schema se necessario."""
        with db_session(self._db_path) as conn:
            init_db(conn)

    def upsert_grid_cells(self, cells: Sequence[GridCell]) -> int:
        """Insere ou atualiza celulas da grade."""
        if not cells:
            return 0
        sql = """
            INSERT INTO grid_cells (
                region_key, lat_center, lon_center, state, row_idx, col_idx
            ) VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(region_key) DO UPDATE SET
                lat_center = excluded.lat_center,
                lon_center = excluded.lon_center,
                state = excluded.state,
                row_idx = excluded.row_idx,
                col_idx = excluded.col_idx
        """
        rows = [
            (
                c.region_key,
                c.lat_center,
                c.lon_center,
                c.state,
                c.row_idx,
                c.col_idx,
            )
            for c in cells
        ]
        return self._executemany(sql, rows)

    def list_grid_cells(self, state: str | None = None) -> list[dict[str, Any]]:
        """Lista celulas; filtro opcional por UF."""
        sql = "SELECT * FROM grid_cells"
        params: tuple[Any, ...] = ()
        if state:
            sql += " WHERE state = ?"
            params = (state.upper(),)
        sql += " ORDER BY row_idx, col_idx"
        return self._fetchall(sql, params)

    def insert_fire_events(self, events: Sequence[FireEvent]) -> int:
        """Insere focos ignorando duplicatas pela chave dedup_key."""
        if not events:
            return 0
        sql = """
            INSERT OR IGNORE INTO fire_events (
                latitude, longitude, acq_date, acq_time, brightness,
                confidence, frp, satellite, instrument, region_key, dedup_key
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        rows = [_fire_event_row(e) for e in events]
        return self._executemany(sql, rows)

    def count_fires_by_region_date(
        self, region_key: str, acq_date: str
    ) -> int:
        """Conta focos em uma celula em um dia."""
        row = self._fetchone(
            """
            SELECT COUNT(*) AS n FROM fire_events
            WHERE region_key = ? AND acq_date = ?
            """,
            (region_key, acq_date),
        )
        return int(row["n"]) if row else 0

    def upsert_weather_daily(self, records: Sequence[WeatherDaily]) -> int:
        """Insere ou atualiza clima diario por celula."""
        if not records:
            return 0
        sql = """
            INSERT INTO weather_daily (
                region_key, weather_date, tmax_c, tmin_c, precip_mm,
                wind_max_kmh, pressure_hpa, source
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(region_key, weather_date) DO UPDATE SET
                tmax_c = excluded.tmax_c,
                tmin_c = excluded.tmin_c,
                precip_mm = excluded.precip_mm,
                wind_max_kmh = excluded.wind_max_kmh,
                pressure_hpa = excluded.pressure_hpa,
                source = excluded.source
        """
        rows = [
            (
                r.region_key,
                r.weather_date,
                r.tmax_c,
                r.tmin_c,
                r.precip_mm,
                r.wind_max_kmh,
                r.pressure_hpa,
                r.source,
            )
            for r in records
        ]
        return self._executemany(sql, rows)

    def get_weather(
        self, region_key: str, weather_date: str
    ) -> dict[str, Any] | None:
        """Busca clima de uma celula em um dia."""
        return self._fetchone(
            """
            SELECT * FROM weather_daily
            WHERE region_key = ? AND weather_date = ?
            """,
            (region_key, weather_date),
        )

    def upsert_risk_scores(self, scores: Sequence[RiskScore]) -> int:
        """Insere ou atualiza scores de risco."""
        if not scores:
            return 0
        sql = """
            INSERT INTO risk_scores (
                region_key, reference_date, probability, risk_score,
                risk_level, priority_rank, model_version
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(region_key, reference_date) DO UPDATE SET
                probability = excluded.probability,
                risk_score = excluded.risk_score,
                risk_level = excluded.risk_level,
                priority_rank = excluded.priority_rank,
                model_version = excluded.model_version,
                computed_at = datetime('now')
        """
        rows = [
            (
                s.region_key,
                s.reference_date,
                s.probability,
                s.risk_score,
                s.risk_level,
                s.priority_rank,
                s.model_version,
            )
            for s in scores
        ]
        return self._executemany(sql, rows)

    def list_risk_scores(
        self,
        reference_date: str,
        risk_level: str | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """Lista scores por data; ordena por prioridade e score."""
        sql = "SELECT * FROM risk_scores WHERE reference_date = ?"
        params: list[Any] = [reference_date]
        if risk_level:
            sql += " AND risk_level = ?"
            params.append(risk_level)
        sql += " ORDER BY priority_rank ASC NULLS LAST, risk_score DESC"
        if limit is not None:
            sql += " LIMIT ?"
            params.append(limit)
        return self._fetchall(sql, tuple(params))

    def _executemany(self, sql: str, rows: Sequence[tuple[Any, ...]]) -> int:
        with db_session(self._db_path) as conn:
            conn.executemany(sql, rows)
            conn.commit()
            return conn.total_changes

    def _fetchall(
        self, sql: str, params: tuple[Any, ...] = ()
    ) -> list[dict[str, Any]]:
        with db_session(self._db_path) as conn:
            cur = conn.execute(sql, params)
            return [_row_to_dict(row) for row in cur.fetchall()]

    def _fetchone(
        self, sql: str, params: tuple[Any, ...] = ()
    ) -> dict[str, Any] | None:
        with db_session(self._db_path) as conn:
            row = conn.execute(sql, params).fetchone()
            return _row_to_dict(row) if row else None


def _fire_event_row(event: FireEvent) -> tuple[Any, ...]:
    return (
        event.latitude,
        event.longitude,
        event.acq_date,
        event.acq_time,
        event.brightness,
        event.confidence,
        event.frp,
        event.satellite,
        event.instrument,
        event.region_key,
        event.dedup_key,
    )


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {key: row[key] for key in row.keys()}
