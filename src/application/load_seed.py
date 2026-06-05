"""Bootstrap do modo offline: seed CSV -> SQLite."""

from __future__ import annotations

import argparse
import sys

from src.config import DB_PATH, OFFLINE_MODE, ensure_data_dirs
from src.infrastructure.db.repository import OrbitFireRepository
from src.infrastructure.seed.loader import SeedLoadReport, load_seed_files


def bootstrap_offline(
    repository: OrbitFireRepository | None = None,
) -> SeedLoadReport:
    """Carrega seed quando OFFLINE_MODE esta ativo."""
    if not OFFLINE_MODE:
        raise RuntimeError(
            "OFFLINE_MODE desativado. Defina OFFLINE_MODE=1 no .env para demo offline."
        )
    ensure_data_dirs()
    repo = repository or OrbitFireRepository(DB_PATH)
    return load_seed_files(repo)


def main(argv: list[str] | None = None) -> int:
    """CLI: python -m src.application.load_seed [--force]."""
    parser = argparse.ArgumentParser(
        description="Carrega dados seed do Centro-Oeste no SQLite."
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Carrega seed mesmo com OFFLINE_MODE desativado.",
    )
    args = parser.parse_args(argv)

    if not OFFLINE_MODE and not args.force:
        print(
            "OFFLINE_MODE desativado. Use --force ou OFFLINE_MODE=1 no .env.",
            file=sys.stderr,
        )
        return 1

    ensure_data_dirs()
    report = load_seed_files(OrbitFireRepository(DB_PATH))
    _print_report(report)
    return 0


def _print_report(report: SeedLoadReport) -> None:
    print(f"Seed carregado de: {report.seed_dir}")
    print(f"  grid_cells:   {report.grid_cells}")
    print(f"  fire_events:  {report.fire_events}")
    print(f"  weather_rows: {report.weather_rows}")


if __name__ == "__main__":
    raise SystemExit(main())
