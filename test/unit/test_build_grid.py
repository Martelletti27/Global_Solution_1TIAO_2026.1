"""Testes de build_grid (S1.E3)."""

from pathlib import Path

import pandas as pd

from src.config import BBox
from src.application.build_grid import build_grid_cells, save_grid_parquet
from src.domain.region_key import resolve_state


def test_build_grid_celulas_com_uf(tmp_path: Path) -> None:
    # Bbox pequena cobrindo area do DF
    bbox = BBox(min_lat=-16.0, max_lat=-15.5, min_lon=-48.0, max_lon=-47.5)
    cells = build_grid_cells(bbox, grid_deg=0.25)
    assert cells
    for cell in cells:
        assert cell.state is not None
        assert cell.region_key.startswith("BR-CO-")
        assert resolve_state(cell.lat_center, cell.lon_center) == cell.state


def test_save_grid_parquet_cria_arquivo(tmp_path: Path) -> None:
    bbox = BBox(min_lat=-16.0, max_lat=-15.5, min_lon=-48.0, max_lon=-47.5)
    cells = build_grid_cells(bbox, grid_deg=0.25)
    out = tmp_path / "grid_cells.parquet"
    path = save_grid_parquet(cells, path=out)
    assert path.is_file()
    df = pd.read_parquet(path)
    assert len(df) == len(cells)
    assert "region_key" in df.columns
