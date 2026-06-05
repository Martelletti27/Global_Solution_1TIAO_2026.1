"""Chaves de regiao e geometria da grade (dominio puro)."""

from __future__ import annotations

from collections.abc import Iterator

from src.config import BBox

REGION_PREFIX = "BR-CO"
STATES = ("GO", "MT", "MS", "DF")

# Caixas aproximadas (lon_min, lon_max, lat_min, lat_max); DF antes dos demais.
_STATE_BBOXES: tuple[tuple[str, tuple[float, float, float, float]], ...] = (
    ("DF", (-48.35, -47.25, -16.05, -15.50)),
    ("MS", (-58.20, -50.20, -24.10, -17.20)),
    ("GO", (-53.30, -45.80, -19.50, -12.40)),
    ("MT", (-61.60, -50.00, -18.00, -7.30)),
)


def format_region_key(state: str, sequence: int) -> str:
    """Monta a chave BR-CO-UF-NN."""
    uf = state.strip().upper()
    if uf not in STATES:
        raise ValueError(f"UF invalida: {state}")
    if sequence < 1 or sequence > 99:
        raise ValueError(f"Sequencia fora do intervalo 1-99: {sequence}")
    return f"{REGION_PREFIX}-{uf}-{sequence:02d}"


def resolve_state(lat: float, lon: float) -> str | None:
    """Retorna a UF cuja bbox aproximada contem o ponto, ou None."""
    for uf, (lon_min, lon_max, lat_min, lat_max) in _STATE_BBOXES:
        if lon_min <= lon <= lon_max and lat_min <= lat <= lat_max:
            return uf
    return None


def cell_center(row_idx: int, col_idx: int, bbox: BBox, grid_deg: float) -> tuple[float, float]:
    """Centro da celula (lat, lon) a partir dos indices na grade."""
    lon = bbox.min_lon + (col_idx + 0.5) * grid_deg
    lat = bbox.max_lat - (row_idx + 0.5) * grid_deg
    return lat, lon


def iter_grid_indices(bbox: BBox, grid_deg: float) -> Iterator[tuple[int, int]]:
    """Itera (row_idx, col_idx) cobrindo a bbox com passo grid_deg."""
    n_rows = int(round((bbox.max_lat - bbox.min_lat) / grid_deg))
    n_cols = int(round((bbox.max_lon - bbox.min_lon) / grid_deg))
    for row in range(n_rows):
        for col in range(n_cols):
            yield row, col
