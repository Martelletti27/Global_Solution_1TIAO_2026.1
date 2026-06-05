"""Leitura dos CSVs em data/seed/ e conversao para modelos do repositorio."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from src.config import DATA_SEED
from src.infrastructure.db.repository import (
    FireEvent,
    GridCell,
    OrbitFireRepository,
    WeatherDaily,
)

SEED_GRID_FILE = "grid_cells.csv"
SEED_FIRES_FILE = "fire_events.csv"
SEED_WEATHER_FILE = "weather_daily.csv"


@dataclass(frozen=True)
class SeedLoadReport:
    """Resumo da carga offline."""

    grid_cells: int
    fire_events: int
    weather_rows: int
    seed_dir: Path


def load_seed_files(
    repository: OrbitFireRepository,
    seed_dir: Path | None = None,
) -> SeedLoadReport:
    """Carrega CSVs seed no SQLite via repositorio."""
    base = seed_dir or DATA_SEED
    grid_path = base / SEED_GRID_FILE
    fires_path = base / SEED_FIRES_FILE
    weather_path = base / SEED_WEATHER_FILE

    _require_file(grid_path)
    _require_file(fires_path)
    _require_file(weather_path)

    repository.initialize()
    grid_count = repository.upsert_grid_cells(_read_grid_cells(grid_path))
    fire_count = repository.insert_fire_events(_read_fire_events(fires_path))
    weather_count = repository.upsert_weather_daily(
        _read_weather_daily(weather_path)
    )

    return SeedLoadReport(
        grid_cells=grid_count,
        fire_events=fire_count,
        weather_rows=weather_count,
        seed_dir=base,
    )


def _require_file(path: Path) -> None:
    if not path.is_file():
        raise FileNotFoundError(f"Arquivo seed nao encontrado: {path}")


def _read_grid_cells(path: Path) -> list[GridCell]:
    rows = _read_dict_rows(path)
    return [
        GridCell(
            region_key=row["region_key"],
            lat_center=float(row["lat_center"]),
            lon_center=float(row["lon_center"]),
            row_idx=int(row["row_idx"]),
            col_idx=int(row["col_idx"]),
            state=row.get("state") or None,
        )
        for row in rows
    ]


def _read_fire_events(path: Path) -> list[FireEvent]:
    rows = _read_dict_rows(path)
    return [
        FireEvent(
            latitude=float(row["latitude"]),
            longitude=float(row["longitude"]),
            acq_date=row["acq_date"],
            dedup_key=row["dedup_key"],
            acq_time=_optional_str(row.get("acq_time")),
            brightness=_optional_float(row.get("brightness")),
            confidence=_optional_str(row.get("confidence")),
            frp=_optional_float(row.get("frp")),
            satellite=_optional_str(row.get("satellite")),
            instrument=_optional_str(row.get("instrument")),
            region_key=_optional_str(row.get("region_key")),
        )
        for row in rows
    ]


def _read_weather_daily(path: Path) -> list[WeatherDaily]:
    rows = _read_dict_rows(path)
    return [
        WeatherDaily(
            region_key=row["region_key"],
            weather_date=row["weather_date"],
            tmax_c=_optional_float(row.get("tmax_c")),
            tmin_c=_optional_float(row.get("tmin_c")),
            precip_mm=_optional_float(row.get("precip_mm")),
            wind_max_kmh=_optional_float(row.get("wind_max_kmh")),
            pressure_hpa=_optional_float(row.get("pressure_hpa")),
            source=_optional_str(row.get("source")),
        )
        for row in rows
    ]


def _read_dict_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _optional_str(value: str | None) -> str | None:
    if value is None or value.strip() == "":
        return None
    return value.strip()


def _optional_float(value: str | None) -> float | None:
    if value is None or value.strip() == "":
        return None
    return float(value)
