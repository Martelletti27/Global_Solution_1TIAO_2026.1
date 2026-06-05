"""Testes do modo offline e carga de seed (S0.E3)."""

from pathlib import Path

import pytest

from src.application.load_seed import bootstrap_offline, main
from src.config import DATA_SEED
from src.infrastructure.db.repository import OrbitFireRepository
from src.infrastructure.seed.loader import load_seed_files


@pytest.fixture
def memory_db(tmp_path: Path) -> Path:
    return tmp_path / "offline.db"


def test_arquivos_seed_existem_no_repositorio() -> None:
    assert (DATA_SEED / "grid_cells.csv").is_file()
    assert (DATA_SEED / "fire_events.csv").is_file()
    assert (DATA_SEED / "weather_daily.csv").is_file()


def test_load_seed_files_popula_banco(memory_db: Path) -> None:
    repo = OrbitFireRepository(memory_db)
    report = load_seed_files(repo, seed_dir=DATA_SEED)

    assert report.grid_cells == 8
    assert report.fire_events == 10
    assert report.weather_rows == 15

    cells = repo.list_grid_cells()
    assert len(cells) == 8
    assert repo.count_fires_by_region_date("BR-CO-MT-01", "2025-08-15") == 1
    weather = repo.get_weather("BR-CO-MT-03", "2025-08-18")
    assert weather is not None
    assert weather["tmax_c"] == 38.2


def test_bootstrap_offline_exige_flag(memory_db: Path, monkeypatch) -> None:
    monkeypatch.setattr("src.application.load_seed.OFFLINE_MODE", False)
    repo = OrbitFireRepository(memory_db)
    with pytest.raises(RuntimeError, match="OFFLINE_MODE"):
        bootstrap_offline(repo)


def test_bootstrap_offline_com_flag(memory_db: Path, monkeypatch) -> None:
    monkeypatch.setattr("src.application.load_seed.DB_PATH", memory_db)
    monkeypatch.setattr("src.application.load_seed.OFFLINE_MODE", True)
    report = bootstrap_offline()
    assert report.grid_cells == 8
    assert report.fire_events == 10


def test_cli_force_sem_offline(memory_db: Path, monkeypatch) -> None:
    monkeypatch.setattr("src.application.load_seed.DB_PATH", memory_db)
    monkeypatch.setattr("src.application.load_seed.OFFLINE_MODE", False)
    code = main(["--force"])
    assert code == 0
    repo = OrbitFireRepository(memory_db)
    assert len(repo.list_grid_cells()) == 8


def test_cli_recusa_sem_force_nem_offline(monkeypatch) -> None:
    monkeypatch.setattr("src.application.load_seed.OFFLINE_MODE", False)
    code = main([])
    assert code == 1
