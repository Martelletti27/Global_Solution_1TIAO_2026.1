"""Testes do cliente Open-Meteo (S1.E2)."""

import json
from pathlib import Path
from unittest.mock import MagicMock

import requests

from src.infrastructure.db.repository import GridCell
from src.infrastructure.weather.client import OpenMeteoClient, parse_open_meteo_archive

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "open_meteo_sample.json"


def test_parse_open_meteo_fixture_multi_local() -> None:
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    cells = [
        GridCell(
            region_key="BR-CO-DF-01",
            lat_center=-15.75,
            lon_center=-47.75,
            row_idx=0,
            col_idx=0,
            state="DF",
        ),
        GridCell(
            region_key="BR-CO-DF-02",
            lat_center=-16.25,
            lon_center=-48.25,
            row_idx=1,
            col_idx=1,
            state="DF",
        ),
    ]
    by_coord = {
        (-15.75, -47.75): [cells[0]],
        (-16.25, -48.25): [cells[1]],
    }
    records = parse_open_meteo_archive(payload, by_coord)
    assert len(records) == 4
    assert records[0].region_key == "BR-CO-DF-01"
    assert records[0].weather_date == "2024-06-01"
    assert records[0].tmax_c == 32.1


def test_fetch_archive_batch_mock_requests() -> None:
    session = MagicMock(spec=requests.Session)
    response = MagicMock()
    response.json.return_value = {"latitude": -15.75, "longitude": -47.75, "daily": {}}
    session.get.return_value = response

    client = OpenMeteoClient(session=session, base_url="https://example.test/archive")
    payload = client.fetch_archive_batch([(-15.75, -47.75)], "2024-06-01", "2024-06-02")
    assert "latitude" in payload
    session.get.assert_called_once()
