"""Pipeline de ingestao de clima: Open-Meteo ou seed -> data/raw/weather -> SQLite."""

from __future__ import annotations

import argparse
import csv
import json
import logging
import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from src.config import (
    DATA_RAW_WEATHER,
    DATA_SEED,
    DB_PATH,
    OFFLINE_MODE,
    OPEN_METEO_ARCHIVE_LAG_DAYS,
    RECENT_DAYS,
    ensure_data_dirs,
)
from src.infrastructure.db.repository import GridCell, OrbitFireRepository, WeatherDaily
from src.infrastructure.weather.client import OpenMeteoClient, coord_key, parse_open_meteo_archive

logger = logging.getLogger(__name__)
SEED_WEATHER_FILE = "weather_daily.csv"


@dataclass(frozen=True)
class WeatherIngestReport:
    """Resumo da ingestao de clima."""

    mode: str
    raw_files: tuple[Path, ...]
    records_parsed: int
    records_upserted: int


def ingest_weather(repository: OrbitFireRepository | None = None) -> WeatherIngestReport:
    """Executa ingestao offline (seed) ou live (Open-Meteo archive)."""
    ensure_data_dirs()
    DATA_RAW_WEATHER.mkdir(parents=True, exist_ok=True)
    repo = repository or OrbitFireRepository(DB_PATH)
    repo.initialize()

    if OFFLINE_MODE:
        return _ingest_offline(repo)

    cells = _list_grid_cells(repo)
    if not cells:
        raise RuntimeError(
            "Grade vazia: execute python -m src.application.build_grid antes do clima."
        )

    start_date, end_date = _date_window()
    client = OpenMeteoClient()
    payloads = client.fetch_archive_for_cells(
        cells,
        start_date.isoformat(),
        end_date.isoformat(),
    )

    cells_by_coord = _cells_by_coord(cells)
    records: list[WeatherDaily] = []
    raw_files: list[Path] = []
    for i, payload in enumerate(payloads):
        raw_path = _save_raw_json(payload, start_date, end_date, i)
        raw_files.append(raw_path)
        records.extend(parse_open_meteo_archive(payload, cells_by_coord))

    upserted = repo.upsert_weather_daily(records)
    return WeatherIngestReport(
        mode="live",
        raw_files=tuple(raw_files),
        records_parsed=len(records),
        records_upserted=upserted,
    )


def _ingest_offline(repository: OrbitFireRepository) -> WeatherIngestReport:
    _load_seed_grid_if_available(repository)
    seed_path = DATA_SEED / SEED_WEATHER_FILE
    if not seed_path.is_file():
        raise FileNotFoundError(f"Seed offline nao encontrado: {seed_path}")

    records = _read_seed_weather(seed_path)
    upserted = repository.upsert_weather_daily(records)
    return WeatherIngestReport(
        mode="offline",
        raw_files=(),
        records_parsed=len(records),
        records_upserted=upserted,
    )


def _load_seed_grid_if_available(repository: OrbitFireRepository) -> None:
    """Carrega grid_cells.csv do seed para satisfazer FK em weather_daily."""
    from src.infrastructure.seed.loader import SEED_GRID_FILE, _read_grid_cells

    grid_path = DATA_SEED / SEED_GRID_FILE
    if grid_path.is_file():
        repository.upsert_grid_cells(_read_grid_cells(grid_path))


def _read_seed_weather(path: Path) -> list[WeatherDaily]:
    rows: list[WeatherDaily] = []
    with path.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            rows.append(
                WeatherDaily(
                    region_key=row["region_key"],
                    weather_date=row["weather_date"],
                    tmax_c=_float_or_none(row.get("tmax_c")),
                    tmin_c=_float_or_none(row.get("tmin_c")),
                    precip_mm=_float_or_none(row.get("precip_mm")),
                    wind_max_kmh=_float_or_none(row.get("wind_max_kmh")),
                    pressure_hpa=_float_or_none(row.get("pressure_hpa")),
                    source=row.get("source") or "seed",
                )
            )
    return rows


def _float_or_none(value: str | None) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


def _date_window() -> tuple[date, date]:
    end_date = date.today() - timedelta(days=OPEN_METEO_ARCHIVE_LAG_DAYS)
    start_date = end_date - timedelta(days=RECENT_DAYS - 1)
    return start_date, end_date


def _list_grid_cells(repository: OrbitFireRepository) -> list[GridCell]:
    raw = repository.list_grid_cells()
    return [
        GridCell(
            region_key=row["region_key"],
            lat_center=float(row["lat_center"]),
            lon_center=float(row["lon_center"]),
            row_idx=int(row["row_idx"]),
            col_idx=int(row["col_idx"]),
            state=row.get("state"),
        )
        for row in raw
    ]


def _cells_by_coord(cells: list[GridCell]) -> dict[tuple[float, float], list[GridCell]]:
    out: dict[tuple[float, float], list[GridCell]] = {}
    for cell in cells:
        key = coord_key(cell.lat_center, cell.lon_center)
        out.setdefault(key, []).append(cell)
    return out


def _save_raw_json(payload: dict, start: date, end: date, batch_idx: int) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = DATA_RAW_WEATHER / f"open_meteo_{start}_{end}_b{batch_idx}_{stamp}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


def main(argv: list[str] | None = None) -> int:
    """CLI: python -m src.infrastructure.weather.ingest."""
    parser = argparse.ArgumentParser(description="Ingestao clima diario (Open-Meteo).")
    parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO)
    try:
        report = ingest_weather()
    except (RuntimeError, ValueError, FileNotFoundError, OSError) as exc:
        print(f"Erro na ingestao de clima: {exc}", file=sys.stderr)
        return 1

    print(f"Modo: {report.mode}")
    print(f"Registros parseados: {report.records_parsed}")
    print(f"Registros gravados: {report.records_upserted}")
    for path in report.raw_files:
        print(f"  raw: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
