"""Cliente HTTP para Open-Meteo Archive API."""

from __future__ import annotations

import logging
from typing import Any

import requests

from src.config import OPEN_METEO_BATCH_SIZE, OPEN_METEO_TIMEZONE, OPEN_METEO_URL
from src.infrastructure.db.repository import GridCell, WeatherDaily

logger = logging.getLogger(__name__)

DAILY_VARS = (
    "temperature_2m_max",
    "temperature_2m_min",
    "precipitation_sum",
    "wind_speed_10m_max",
    "surface_pressure_mean",
)


class OpenMeteoClient:
    """Consulta clima diario historico por lote de coordenadas."""

    def __init__(
        self,
        session: requests.Session | None = None,
        base_url: str | None = None,
    ) -> None:
        self._session = session or requests.Session()
        self._base_url = (base_url or OPEN_METEO_URL).rstrip("/")

    def fetch_archive_batch(
        self,
        points: list[tuple[float, float]],
        start_date: str,
        end_date: str,
    ) -> dict[str, Any]:
        if not points:
            return {}
        lats = ",".join(f"{lat:.6f}" for lat, _ in points)
        lons = ",".join(f"{lon:.6f}" for _, lon in points)
        params = {
            "latitude": lats,
            "longitude": lons,
            "start_date": start_date,
            "end_date": end_date,
            "daily": ",".join(DAILY_VARS),
            "timezone": OPEN_METEO_TIMEZONE,
        }
        resp = self._session.get(self._base_url, params=params, timeout=120)
        resp.raise_for_status()
        return resp.json()

    def fetch_archive_for_cells(
        self,
        cells: list[GridCell],
        start_date: str,
        end_date: str,
    ) -> list[dict[str, Any]]:
        payloads: list[dict[str, Any]] = []
        batch: list[tuple[float, float]] = []
        for cell in cells:
            batch.append((cell.lat_center, cell.lon_center))
            if len(batch) >= OPEN_METEO_BATCH_SIZE:
                payloads.append(self.fetch_archive_batch(batch, start_date, end_date))
                batch = []
        if batch:
            payloads.append(self.fetch_archive_batch(batch, start_date, end_date))
        return payloads


def coord_key(lat: float, lon: float) -> tuple[float, float]:
    """Chave estavel para casar coordenadas com celulas da grade."""
    return round(lat, 4), round(lon, 4)


def parse_open_meteo_archive(
    payload: dict[str, Any],
    cells_by_coord: dict[tuple[float, float], list[GridCell]],
) -> list[WeatherDaily]:
    """Converte resposta multi-localidade em registros WeatherDaily."""
    results: list[WeatherDaily] = []
    if not payload:
        return results

    latitudes = payload.get("latitude")
    longitudes = payload.get("longitude")
    daily_root = payload.get("daily") or {}

    if isinstance(latitudes, list):
        for idx, lat in enumerate(latitudes):
            lon = longitudes[idx]
            daily = {
                key: values[idx]
                for key, values in daily_root.items()
                if isinstance(values, list) and len(values) > idx
            }
            results.extend(_parse_single_location(lat, lon, daily, cells_by_coord))
    else:
        results.extend(
            _parse_single_location(
                float(latitudes),
                float(longitudes),
                daily_root,
                cells_by_coord,
            )
        )
    return results


def _parse_single_location(
    lat: float,
    lon: float,
    daily: dict[str, Any],
    cells_by_coord: dict[tuple[float, float], list[GridCell]],
) -> list[WeatherDaily]:
    key = coord_key(lat, lon)
    cells = cells_by_coord.get(key, [])
    dates = daily.get("time") or []
    out: list[WeatherDaily] = []
    for i, day_str in enumerate(dates):
        for cell in cells:
            out.append(
                WeatherDaily(
                    region_key=cell.region_key,
                    weather_date=day_str,
                    tmax_c=_series_value(daily, "temperature_2m_max", i),
                    tmin_c=_series_value(daily, "temperature_2m_min", i),
                    precip_mm=_series_value(daily, "precipitation_sum", i),
                    wind_max_kmh=_series_value(daily, "wind_speed_10m_max", i),
                    pressure_hpa=_series_value(daily, "surface_pressure_mean", i),
                    source="open-meteo",
                )
            )
    return out


def _series_value(daily: dict[str, Any], key: str, index: int) -> float | None:
    series = daily.get(key)
    if not series or index >= len(series):
        return None
    value = series[index]
    return None if value is None else float(value)
