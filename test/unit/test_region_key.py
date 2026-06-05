"""Testes de region_key (S1.E3)."""

from src.config import BBox
from src.domain.region_key import cell_center, format_region_key, resolve_state


def test_format_region_key_padrao() -> None:
    assert format_region_key("mt", 1) == "BR-CO-MT-01"
    assert format_region_key("GO", 12) == "BR-CO-GO-12"


def test_format_region_key_rejeita_uf_invalida() -> None:
    try:
        format_region_key("SP", 1)
    except ValueError:
        pass
    else:
        raise AssertionError("esperava ValueError")


def test_resolve_state_df_prioridade() -> None:
    # Ponto tipico do DF (dentro da bbox aproximada de DF)
    assert resolve_state(-15.78, -47.92) == "DF"


def test_resolve_state_fora_da_regiao() -> None:
    assert resolve_state(-10.0, -40.0) is None


def test_cell_center_indices() -> None:
    bbox = BBox(min_lat=-16.0, max_lat=-15.5, min_lon=-48.0, max_lon=-47.5)
    lat, lon = cell_center(0, 0, bbox, grid_deg=0.25)
    assert lon == bbox.min_lon + 0.125
    assert lat == bbox.max_lat - 0.125
