"""Testes da ingestao de clima (S1.E2)."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.config import DATA_SEED
from src.infrastructure.db.repository import OrbitFireRepository
from src.infrastructure.weather.ingest import ingest_weather


def test_ingest_offline_grava_clima(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "orbitfire.db"
    monkeypatch.setattr("src.infrastructure.weather.ingest.DB_PATH", db_path)
    monkeypatch.setattr("src.infrastructure.weather.ingest.DATA_SEED", DATA_SEED)
    monkeypatch.setattr("src.infrastructure.weather.ingest.OFFLINE_MODE", True)

    report = ingest_weather()

    assert report.mode == "offline"
    assert report.records_parsed == 15
    assert report.records_upserted == 15

    repo = OrbitFireRepository(db_path)
    weather = repo.get_weather("BR-CO-MT-03", "2025-08-18")
    assert weather is not None
    assert weather["tmax_c"] == 38.2


@patch("src.infrastructure.weather.ingest.OpenMeteoClient")
def test_ingest_live_exige_grade(
    mock_client_cls: MagicMock, tmp_path: Path, monkeypatch
) -> None:
    db_path = tmp_path / "orbitfire.db"
    monkeypatch.setattr("src.infrastructure.weather.ingest.DB_PATH", db_path)
    monkeypatch.setattr("src.infrastructure.weather.ingest.OFFLINE_MODE", False)

    with pytest.raises(RuntimeError, match="Grade vazia"):
        ingest_weather()
