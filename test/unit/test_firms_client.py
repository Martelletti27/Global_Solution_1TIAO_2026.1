"""Testes do cliente e ingestao FIRMS (S1.E1)."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests

from src.config import BBOX, DATA_RAW_FIRMS, DATA_SEED
from src.infrastructure.db.repository import OrbitFireRepository
from src.infrastructure.firms.client import (
    FirmsApiError,
    FirmsClient,
    build_dedup_key,
    clamp_firms_days,
    parse_firms_csv,
)
from src.infrastructure.firms.ingest import ingest_firms

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"
SAMPLE_CSV = (FIXTURES / "firms_area_sample.csv").read_text(encoding="utf-8")


def test_build_area_url_format() -> None:
    client = FirmsClient(map_key="test-key", default_source="VIIRS_SNPP_NRT")
    url = client.build_area_url(days=3)
    assert url.endswith("/VIIRS_SNPP_NRT/-61.6,-24.1,-45.0,-12.0/3")
    assert "/area/csv/test-key/" in url


def test_clamp_firms_days_respeita_limite_api() -> None:
    assert clamp_firms_days(0) == 1
    assert clamp_firms_days(3) == 3
    assert clamp_firms_days(7) == 5
    assert clamp_firms_days(99) == 5


def test_build_area_url_exige_map_key() -> None:
    client = FirmsClient(map_key="")
    with pytest.raises(ValueError, match="FIRMS_MAP_KEY"):
        client.build_area_url()


def test_build_dedup_key_estavel() -> None:
    key = build_dedup_key(-15.48, -56.24, "2025-08-15", "1420", "N")
    assert key == "N_-15.4800_-56.2400_2025-08-15_1420"


def test_parse_firms_csv_nativo() -> None:
    events = parse_firms_csv(SAMPLE_CSV, bbox=BBOX)
    assert len(events) == 3
    assert events[0].acq_date == "2025-08-15"
    assert events[0].confidence == "n"
    assert events[0].dedup_key.startswith("N_")


def test_parse_firms_csv_viirs_bright_ti4() -> None:
    csv_text = (
        "latitude,longitude,bright_ti4,scan,track,acq_date,acq_time,"
        "satellite,instrument,confidence,version,bright_ti5,frp,daynight\n"
        "-15.48,-56.24,341.2,0.39,0.36,2025-08-15,1420,N,VIIRS,n,2.0NRT,310.0,5.1,D\n"
    )
    events = parse_firms_csv(csv_text, bbox=BBOX)
    assert len(events) == 1
    assert events[0].brightness == 341.2


def test_parse_firms_csv_apenas_cabecalho() -> None:
    csv_text = "latitude,longitude,acq_date,acq_time,satellite\n"
    assert parse_firms_csv(csv_text) == []


def test_parse_firms_csv_filtra_fora_do_bbox() -> None:
    csv_text = SAMPLE_CSV + "99.0,0.0,100,0.3,0.3,2025-08-15,1200,N,VIIRS,n,2.0,90,1.0,D\n"
    events = parse_firms_csv(csv_text, bbox=BBOX)
    assert len(events) == 3


@patch("src.infrastructure.firms.client.requests.get")
def test_fetch_area_csv(mock_get: MagicMock) -> None:
    mock_response = MagicMock()
    mock_response.text = SAMPLE_CSV
    mock_response.raise_for_status = MagicMock()
    mock_get.return_value = mock_response

    client = FirmsClient(map_key="abc")
    result = client.fetch_area_csv(days=3)

    assert result.days == 3
    assert "latitude" in result.csv_text
    mock_get.assert_called_once()


@patch("src.infrastructure.firms.client.requests.get")
def test_fetch_area_csv_http_error(mock_get: MagicMock) -> None:
    mock_response = MagicMock()
    mock_response.status_code = 403
    mock_response.text = "forbidden"
    mock_response.raise_for_status.side_effect = requests.HTTPError("403")
    mock_get.return_value = mock_response

    client = FirmsClient(map_key="abc")
    with pytest.raises(FirmsApiError, match="403"):
        client.fetch_area_csv()


def test_source_invalido_rejeitado() -> None:
    with pytest.raises(ValueError, match="SOURCE FIRMS invalido"):
        FirmsClient(map_key="abc", default_source="INVALID_SOURCE")


def test_ingest_offline_salva_raw_e_banco(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "orbitfire.db"
    raw_firms = tmp_path / "raw" / "firms"
    monkeypatch.setattr("src.infrastructure.firms.ingest.DB_PATH", db_path)
    monkeypatch.setattr("src.infrastructure.firms.ingest.DATA_RAW_FIRMS", raw_firms)
    monkeypatch.setattr("src.infrastructure.firms.ingest.DATA_SEED", DATA_SEED)
    monkeypatch.setattr("src.infrastructure.firms.ingest.OFFLINE_MODE", True)

    report = ingest_firms()

    assert report.mode == "offline"
    assert report.events_parsed == 10
    assert report.events_inserted == 10
    assert len(report.raw_files) == 1
    assert report.raw_files[0].parent == raw_firms

    repo = OrbitFireRepository(db_path)
    assert repo.count_fires_by_region_date("BR-CO-MT-01", "2025-08-15") == 1


@patch("src.infrastructure.firms.ingest.FirmsClient")
def test_ingest_live_duas_fontes(
    mock_client_cls: MagicMock, tmp_path: Path, monkeypatch
) -> None:
    db_path = tmp_path / "orbitfire.db"
    raw_firms = tmp_path / "raw" / "firms"
    monkeypatch.setattr("src.infrastructure.firms.ingest.DB_PATH", db_path)
    monkeypatch.setattr("src.infrastructure.firms.ingest.DATA_RAW_FIRMS", raw_firms)
    monkeypatch.setattr("src.infrastructure.firms.ingest.OFFLINE_MODE", False)
    monkeypatch.setattr("src.infrastructure.firms.ingest.is_firms_configured", lambda: True)

    mock_client = MagicMock()
    mock_client.fetch_area_csv.side_effect = [
        MagicMock(csv_text=SAMPLE_CSV, source="VIIRS_SNPP_NRT", days=5, area="x"),
        MagicMock(csv_text=SAMPLE_CSV, source="VIIRS_SNPP_SP", days=5, area="x"),
    ]
    mock_client_cls.return_value = mock_client

    report = ingest_firms(include_archive=True)

    assert report.mode == "live"
    assert report.events_parsed == 6
    assert len(report.raw_files) == 2
    assert mock_client.fetch_area_csv.call_count == 2
