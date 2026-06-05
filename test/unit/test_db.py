"""Testes do schema SQLite e repositorio (S0.E2)."""

from pathlib import Path

import pytest

from src.infrastructure.db.repository import (
    FireEvent,
    GridCell,
    OrbitFireRepository,
    RiskScore,
    WeatherDaily,
)
from src.infrastructure.db.schema import get_schema_version, init_db
from src.infrastructure.db.connection import db_session


@pytest.fixture
def memory_db(tmp_path: Path) -> Path:
    return tmp_path / "test_orbitfire.db"


@pytest.fixture
def repo(memory_db: Path) -> OrbitFireRepository:
    repository = OrbitFireRepository(memory_db)
    repository.initialize()
    return repository


def test_init_db_cria_tabelas(memory_db: Path) -> None:
    with db_session(memory_db) as conn:
        init_db(conn)
        tables = {
            row["name"]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        version = get_schema_version(conn)
    assert "grid_cells" in tables
    assert "fire_events" in tables
    assert "weather_daily" in tables
    assert "risk_scores" in tables
    assert version == 1


def test_init_db_registra_versao(memory_db: Path) -> None:
    with db_session(memory_db) as conn:
        init_db(conn)
        version = get_schema_version(conn)
    assert version == 1


def test_upsert_grid_cells(repo: OrbitFireRepository) -> None:
    cells = [
        GridCell("BR-CO-0-0", -15.0, -56.0, 0, 0, "MT"),
        GridCell("BR-CO-0-1", -15.0, -55.75, 0, 1, "MT"),
    ]
    inserted = repo.upsert_grid_cells(cells)
    assert inserted == 2
    listed = repo.list_grid_cells(state="MT")
    assert len(listed) == 2
    assert listed[0]["region_key"] == "BR-CO-0-0"


def test_insert_fire_events_dedup(repo: OrbitFireRepository) -> None:
    repo.upsert_grid_cells(
        [GridCell("BR-CO-1-1", -14.5, -55.5, 1, 1, "GO")]
    )
    events = [
        FireEvent(
            latitude=-14.5,
            longitude=-55.5,
            acq_date="2025-08-01",
            dedup_key="foco-001",
            region_key="BR-CO-1-1",
            satellite="N",
            confidence="high",
        ),
        FireEvent(
            latitude=-14.5,
            longitude=-55.5,
            acq_date="2025-08-01",
            dedup_key="foco-001",
            region_key="BR-CO-1-1",
        ),
    ]
    repo.insert_fire_events(events)
    count = repo.count_fires_by_region_date("BR-CO-1-1", "2025-08-01")
    assert count == 1


def test_upsert_weather_daily(repo: OrbitFireRepository) -> None:
    repo.upsert_grid_cells(
        [GridCell("BR-CO-2-2", -13.0, -54.0, 2, 2, "MS")]
    )
    record = WeatherDaily(
        region_key="BR-CO-2-2",
        weather_date="2025-09-10",
        tmax_c=35.2,
        precip_mm=0.0,
        source="open-meteo",
    )
    repo.upsert_weather_daily([record])
    fetched = repo.get_weather("BR-CO-2-2", "2025-09-10")
    assert fetched is not None
    assert fetched["tmax_c"] == 35.2

    updated = WeatherDaily(
        region_key="BR-CO-2-2",
        weather_date="2025-09-10",
        tmax_c=36.0,
        precip_mm=1.5,
        source="open-meteo",
    )
    repo.upsert_weather_daily([updated])
    fetched2 = repo.get_weather("BR-CO-2-2", "2025-09-10")
    assert fetched2 is not None
    assert fetched2["tmax_c"] == 36.0


def test_upsert_risk_scores_e_ranking(repo: OrbitFireRepository) -> None:
    repo.upsert_grid_cells(
        [
            GridCell("BR-CO-A", -15.0, -56.0, 0, 0, "MT"),
            GridCell("BR-CO-B", -16.0, -55.0, 1, 0, "GO"),
        ]
    )
    scores = [
        RiskScore("BR-CO-A", "2025-10-01", 0.82, 82, "alto", 2, "v0"),
        RiskScore("BR-CO-B", "2025-10-01", 0.91, 91, "critico", 1, "v0"),
    ]
    repo.upsert_risk_scores(scores)
    top = repo.list_risk_scores("2025-10-01", limit=1)
    assert len(top) == 1
    assert top[0]["region_key"] == "BR-CO-B"
    assert top[0]["risk_level"] == "critico"
