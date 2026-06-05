"""Testes da configuracao central (S0.E1)."""

from pathlib import Path

from src.config import (
    BBOX,
    DATA_DIR,
    DATA_MODELS,
    DATA_PROCESSED,
    DATA_RAW,
    DATA_SEED,
    GRID_DEG,
    PROJECT_ROOT,
    REGION,
    STATES,
    ensure_data_dirs,
    is_firms_configured,
)


def test_region_centro_oeste() -> None:
    assert REGION == "centro-oeste"
    assert STATES == ("GO", "MT", "MS", "DF")


def test_bbox_valores_escopo() -> None:
    assert BBOX.min_lat == -24.1
    assert BBOX.max_lat == -12.0
    assert BBOX.min_lon == -61.6
    assert BBOX.max_lon == -45.0


def test_bbox_firms_format() -> None:
    assert BBOX.as_firms_area() == "-61.6,-24.1,-45.0,-12.0"


def test_paths_relativos_a_raiz() -> None:
    assert (PROJECT_ROOT / "src" / "config.py").is_file()
    assert DATA_DIR == PROJECT_ROOT / "data"
    assert DATA_RAW == DATA_DIR / "raw"
    assert DATA_PROCESSED == DATA_DIR / "processed"
    assert DATA_SEED == DATA_DIR / "seed"
    assert DATA_MODELS == DATA_DIR / "models"


def test_grid_deg_positivo() -> None:
    assert 0 < GRID_DEG <= 1.0


def test_ensure_data_dirs_cria_pastas(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("src.config.DATA_RAW", tmp_path / "raw")
    monkeypatch.setattr("src.config.DATA_PROCESSED", tmp_path / "processed")
    monkeypatch.setattr("src.config.DATA_SEED", tmp_path / "seed")
    monkeypatch.setattr("src.config.DATA_MODELS", tmp_path / "models")

    ensure_data_dirs()

    assert (tmp_path / "raw").is_dir()
    assert (tmp_path / "processed").is_dir()
    assert (tmp_path / "seed").is_dir()
    assert (tmp_path / "models").is_dir()


def test_is_firms_configured_offline(monkeypatch) -> None:
    monkeypatch.setattr("src.config.OFFLINE_MODE", True)
    monkeypatch.setattr("src.config.FIRMS_MAP_KEY", "")
    assert is_firms_configured() is True


def test_is_firms_configured_com_chave(monkeypatch) -> None:
    monkeypatch.setattr("src.config.OFFLINE_MODE", False)
    monkeypatch.setattr("src.config.FIRMS_MAP_KEY", "abc123")
    assert is_firms_configured() is True
