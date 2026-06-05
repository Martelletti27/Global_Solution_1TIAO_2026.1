"""Construcao e persistencia da grade de celulas."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from src.config import BBOX, DATA_PROCESSED, DB_PATH, GRID_DEG, ensure_data_dirs
from src.domain.region_key import cell_center, format_region_key, iter_grid_indices, resolve_state
from src.infrastructure.db.repository import GridCell, OrbitFireRepository


@dataclass(frozen=True)
class BuildGridReport:
    """Resumo da geracao da grade."""

    total_cells: int
    cells_by_state: dict[str, int]
    parquet_path: Path


def build_grid_cells(bbox, grid_deg: float) -> list[GridCell]:
    """Gera celulas com region_key apenas onde resolve_state retorna UF."""
    cells: list[GridCell] = []
    seq_by_state: dict[str, int] = {}
    for row_idx, col_idx in iter_grid_indices(bbox, grid_deg):
        lat, lon = cell_center(row_idx, col_idx, bbox, grid_deg)
        state = resolve_state(lat, lon)
        if state is None:
            continue
        seq_by_state[state] = seq_by_state.get(state, 0) + 1
        region_key = format_region_key(state, seq_by_state[state])
        cells.append(
            GridCell(
                region_key=region_key,
                lat_center=lat,
                lon_center=lon,
                row_idx=row_idx,
                col_idx=col_idx,
                state=state,
            )
        )
    return cells


def save_grid_parquet(cells: list[GridCell], path: Path | None = None) -> Path:
    """Salva a grade em Parquet."""
    ensure_data_dirs()
    out = path or (DATA_PROCESSED / "grid_cells.parquet")
    rows = [
        {
            "region_key": c.region_key,
            "lat_center": c.lat_center,
            "lon_center": c.lon_center,
            "state": c.state,
            "row_idx": c.row_idx,
            "col_idx": c.col_idx,
        }
        for c in cells
    ]
    pd.DataFrame(rows).to_parquet(out, index=False)
    return out


def build_and_persist_grid(
    repository: OrbitFireRepository | None = None,
) -> BuildGridReport:
    """Constroi a grade, persiste no banco e exporta Parquet."""
    repo = repository or OrbitFireRepository(DB_PATH)
    repo.initialize()
    cells = build_grid_cells(BBOX, GRID_DEG)
    repo.upsert_grid_cells(cells)
    parquet_path = save_grid_parquet(cells)
    by_state: dict[str, int] = {}
    for c in cells:
        if c.state:
            by_state[c.state] = by_state.get(c.state, 0) + 1
    return BuildGridReport(
        total_cells=len(cells),
        cells_by_state=by_state,
        parquet_path=parquet_path,
    )


def main() -> int:
    """CLI: python -m src.application.build_grid."""
    report = build_and_persist_grid()
    print(f"Celulas: {report.total_cells}")
    print(f"Por UF: {report.cells_by_state}")
    print(f"Parquet: {report.parquet_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
