"""Pipeline de ingestao FIRMS: API ou seed -> data/raw/firms -> SQLite."""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from src.config import (
    BBOX,
    DATA_RAW_FIRMS,
    DATA_SEED,
    DB_PATH,
    FIRMS_DAYS,
    FIRMS_SOURCE,
    OFFLINE_MODE,
    ensure_data_dirs,
    is_firms_configured,
)
from src.infrastructure.db.repository import FireEvent, OrbitFireRepository
from src.infrastructure.firms.client import (
    FirmsClient,
    clamp_firms_days,
    parse_firms_csv,
)

# Fonte complementar para historico recente (standard processing)
FIRMS_ARCHIVE_SOURCE = "VIIRS_SNPP_SP"


@dataclass(frozen=True)
class FirmsIngestReport:
    """Resumo da ingestao FIRMS."""

    mode: str
    raw_files: tuple[Path, ...]
    events_parsed: int
    events_inserted: int
    sources: tuple[str, ...]


def ingest_firms(
    repository: OrbitFireRepository | None = None,
    include_archive: bool = True,
) -> FirmsIngestReport:
    """Executa ingestao NRT (e opcionalmente historico) para o Centro-Oeste."""
    ensure_data_dirs()
    DATA_RAW_FIRMS.mkdir(parents=True, exist_ok=True)
    repo = repository or OrbitFireRepository(DB_PATH)
    repo.initialize()

    if OFFLINE_MODE:
        return _ingest_offline(repo)

    if not is_firms_configured():
        raise RuntimeError(
            "FIRMS nao configurado. Defina FIRMS_MAP_KEY ou OFFLINE_MODE=1."
        )

    client = FirmsClient()
    raw_files: list[Path] = []
    sources: list[str] = []
    all_events: list[FireEvent] = []

    day_count = clamp_firms_days(FIRMS_DAYS)
    nrt = client.fetch_area_csv(source=FIRMS_SOURCE, days=day_count)
    nrt_path = _save_raw_csv(nrt.csv_text, FIRMS_SOURCE, "nrt")
    raw_files.append(nrt_path)
    sources.append(FIRMS_SOURCE)
    all_events.extend(parse_firms_csv(nrt.csv_text, bbox=BBOX))

    if include_archive and FIRMS_ARCHIVE_SOURCE != FIRMS_SOURCE:
        archive = client.fetch_area_csv(
            source=FIRMS_ARCHIVE_SOURCE,
            days=day_count,
        )
        archive_path = _save_raw_csv(
            archive.csv_text, FIRMS_ARCHIVE_SOURCE, "archive"
        )
        raw_files.append(archive_path)
        sources.append(FIRMS_ARCHIVE_SOURCE)
        all_events.extend(parse_firms_csv(archive.csv_text, bbox=BBOX))

    inserted = repo.insert_fire_events(all_events)
    return FirmsIngestReport(
        mode="live",
        raw_files=tuple(raw_files),
        events_parsed=len(all_events),
        events_inserted=inserted,
        sources=tuple(sources),
    )


def _ingest_offline(repository: OrbitFireRepository) -> FirmsIngestReport:
    """Copia seed local para raw/firms e persiste no banco."""
    _load_seed_grid_if_available(repository)

    seed_path = DATA_SEED / "fire_events.csv"
    if not seed_path.is_file():
        raise FileNotFoundError(f"Seed offline nao encontrado: {seed_path}")

    csv_text = seed_path.read_text(encoding="utf-8")
    raw_path = _save_raw_csv(csv_text, "seed", "offline")
    events = parse_firms_csv(csv_text, bbox=BBOX)
    inserted = repository.insert_fire_events(events)

    return FirmsIngestReport(
        mode="offline",
        raw_files=(raw_path,),
        events_parsed=len(events),
        events_inserted=inserted,
        sources=("seed",),
    )


def _load_seed_grid_if_available(repository: OrbitFireRepository) -> None:
    """Carrega grid_cells.csv do seed para satisfazer FK em fire_events."""
    from src.infrastructure.seed.loader import SEED_GRID_FILE, _read_grid_cells

    grid_path = DATA_SEED / SEED_GRID_FILE
    if grid_path.is_file():
        repository.upsert_grid_cells(_read_grid_cells(grid_path))


def _save_raw_csv(csv_text: str, source: str, label: str) -> Path:
    """Grava snapshot CSV em data/raw/firms/."""
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    safe_source = source.lower().replace(" ", "_")
    path = DATA_RAW_FIRMS / f"firms_{label}_{safe_source}_{stamp}.csv"
    path.write_text(csv_text.strip() + "\n", encoding="utf-8")
    return path


def main(argv: list[str] | None = None) -> int:
    """CLI: python -m src.infrastructure.firms.ingest."""
    parser = argparse.ArgumentParser(description="Ingestao NASA FIRMS (Centro-Oeste).")
    parser.add_argument(
        "--no-archive",
        action="store_true",
        help="Nao baixa fonte historica complementar (VIIRS_SNPP_SP).",
    )
    args = parser.parse_args(argv)

    try:
        report = ingest_firms(include_archive=not args.no_archive)
    except (RuntimeError, ValueError, FileNotFoundError, OSError) as exc:
        print(f"Erro na ingestao FIRMS: {exc}", file=sys.stderr)
        return 1

    _print_report(report)
    return 0


def _print_report(report: FirmsIngestReport) -> None:
    print(f"Modo: {report.mode}")
    print(f"Fontes: {', '.join(report.sources)}")
    print(f"Eventos parseados: {report.events_parsed}")
    print(f"Eventos inseridos: {report.events_inserted}")
    for path in report.raw_files:
        print(f"  raw: {path}")


if __name__ == "__main__":
    raise SystemExit(main())
