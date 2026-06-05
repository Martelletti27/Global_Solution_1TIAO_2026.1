"""Cliente HTTP para API NASA FIRMS (area CSV).



Regras oficiais (https://firms.modaps.eosdis.nasa.gov/api/area/):

- URL: /api/area/csv/{MAP_KEY}/{SOURCE}/{west,south,east,north}/{DAY_RANGE}

- DAY_RANGE: 1 a 5 (consultas maiores consomem mais transacoes)

- Limite: 5000 transacoes por janela de 10 minutos por MAP_KEY

- Coordenadas: west,south,east,north (nao usar north/south/east/west isolados)

"""



from __future__ import annotations



import csv

import io

import time

from dataclasses import dataclass



import requests



from src.config import (

    BBox,

    FIRMS_BASE_URL,

    FIRMS_BBOX,

    FIRMS_DAYS,

    FIRMS_MAP_KEY,

    FIRMS_MIN_REQUEST_INTERVAL_SEC,

    FIRMS_SOURCE,

)

from src.infrastructure.db.repository import FireEvent



# Limite oficial da API area/csv (documentacao FIRMS)

FIRMS_MAX_DAYS = 5

FIRMS_MIN_DAYS = 1



# Fontes suportadas pelo endpoint area (exceto LANDSAT_NRT: so EUA/Canada)

FIRMS_VALID_SOURCES: frozenset[str] = frozenset(

    {

        "LANDSAT_NRT",

        "MODIS_NRT",

        "MODIS_SP",

        "VIIRS_NOAA20_NRT",

        "VIIRS_NOAA20_SP",

        "VIIRS_NOAA21_NRT",

        "VIIRS_SNPP_NRT",

        "VIIRS_SNPP_SP",

    }

)



MAP_KEY_STATUS_URL = "https://firms.modaps.eosdis.nasa.gov/mapserver/mapkey_status/"





class FirmsApiError(RuntimeError):

    """Erro de consulta FIRMS com contexto para o operador."""





@dataclass(frozen=True)

class FirmsFetchResult:

    """Resultado bruto de uma consulta FIRMS."""



    source: str

    days: int

    area: str

    csv_text: str





@dataclass(frozen=True)

class FirmsMapKeyStatus:

    """Uso da MAP_KEY na janela atual (endpoint mapkey_status)."""



    transaction_limit: int

    current_transactions: int

    transaction_interval: str





class FirmsClient:

    """Baixa focos de calor da API FIRMS para uma area geografica."""



    def __init__(

        self,

        map_key: str | None = None,

        base_url: str = FIRMS_BASE_URL,

        default_source: str = FIRMS_SOURCE,

        bbox: BBox = FIRMS_BBOX,

        timeout_seconds: int = 60,

        min_request_interval_sec: float = FIRMS_MIN_REQUEST_INTERVAL_SEC,

    ) -> None:

        if map_key is None:
            self._map_key = FIRMS_MAP_KEY.strip()
        else:
            self._map_key = map_key.strip()

        self._base_url = base_url.rstrip("/")

        self._default_source = _validate_source(default_source)

        self._bbox = bbox

        self._timeout = timeout_seconds

        self._min_interval = max(0.0, min_request_interval_sec)

        self._last_request_at: float | None = None



    def build_area_url(

        self,

        source: str | None = None,

        days: int | None = None,

        bbox: BBox | None = None,

    ) -> str:

        """Monta URL area/csv: /api/area/csv/{key}/{source}/{west,south,east,north}/{days}."""

        if not self._map_key:

            raise ValueError("FIRMS_MAP_KEY nao configurada.")

        src = _validate_source(source or self._default_source)

        day_count = clamp_firms_days(days or FIRMS_DAYS)

        area = (bbox or self._bbox).as_firms_area()

        return f"{self._base_url}/area/csv/{self._map_key}/{src}/{area}/{day_count}"



    def fetch_area_csv(

        self,

        source: str | None = None,

        days: int | None = None,

        bbox: BBox | None = None,

    ) -> FirmsFetchResult:

        """Consulta API FIRMS e retorna CSV como texto."""

        self._wait_between_requests()

        url = self.build_area_url(source=source, days=days, bbox=bbox)

        response = requests.get(url, timeout=self._timeout)

        self._last_request_at = time.monotonic()

        _raise_for_firms_status(response)

        csv_text = response.text.strip()

        if not _looks_like_firms_csv(csv_text):

            raise FirmsApiError(

                "Resposta FIRMS invalida (esperado CSV com latitude/longitude). "

                "Verifique MAP_KEY, SOURCE e DAY_RANGE (1-5)."

            )

        return FirmsFetchResult(

            source=_validate_source(source or self._default_source),

            days=clamp_firms_days(days or FIRMS_DAYS),

            area=(bbox or self._bbox).as_firms_area(),

            csv_text=csv_text,

        )



    def get_map_key_status(self) -> FirmsMapKeyStatus:

        """Consulta saldo de transacoes da MAP_KEY (nao consome area/csv)."""

        if not self._map_key:

            raise ValueError("FIRMS_MAP_KEY nao configurada.")

        url = f"{MAP_KEY_STATUS_URL}?MAP_KEY={self._map_key}"

        response = requests.get(url, timeout=self._timeout)

        response.raise_for_status()

        payload = response.json()

        return FirmsMapKeyStatus(

            transaction_limit=int(payload["transaction_limit"]),

            current_transactions=int(payload["current_transactions"]),

            transaction_interval=str(payload["transaction_interval"]),

        )



    def _wait_between_requests(self) -> None:

        if self._last_request_at is None or self._min_interval <= 0:

            return

        elapsed = time.monotonic() - self._last_request_at

        remaining = self._min_interval - elapsed

        if remaining > 0:

            time.sleep(remaining)





def clamp_firms_days(days: int) -> int:

    """Garante DAY_RANGE dentro do intervalo aceito pela API (1-5)."""

    if days < FIRMS_MIN_DAYS:

        return FIRMS_MIN_DAYS

    return min(days, FIRMS_MAX_DAYS)





def build_dedup_key(

    latitude: float,

    longitude: float,

    acq_date: str,

    acq_time: str | None,

    satellite: str | None,

) -> str:

    """Chave unica para deduplicar focos no SQLite."""

    sat = (satellite or "NA").strip()

    time_part = (acq_time or "0000").strip()

    return f"{sat}_{latitude:.4f}_{longitude:.4f}_{acq_date}_{time_part}"





def parse_firms_csv(

    csv_text: str,

    bbox: BBox | None = None,

) -> list[FireEvent]:

    """Converte CSV FIRMS (ou seed simplificado) em lista de FireEvent."""

    reader = csv.DictReader(io.StringIO(csv_text.strip()))

    if not reader.fieldnames:

        return []



    events: list[FireEvent] = []

    for row in reader:

        event = _row_to_fire_event(row)

        if event is None:

            continue

        if bbox and not _inside_bbox(event.latitude, event.longitude, bbox):

            continue

        events.append(event)

    return events





def _validate_source(source: str) -> str:

    value = source.strip()

    if value not in FIRMS_VALID_SOURCES:

        allowed = ", ".join(sorted(FIRMS_VALID_SOURCES))

        raise ValueError(f"SOURCE FIRMS invalido: {value}. Valores: {allowed}")

    return value





def _looks_like_firms_csv(csv_text: str) -> bool:

    if not csv_text:

        return False

    first_line = csv_text.splitlines()[0].lower()

    return "latitude" in first_line and "longitude" in first_line





def _raise_for_firms_status(response: requests.Response) -> None:

    try:

        response.raise_for_status()

    except requests.HTTPError as exc:

        status = response.status_code

        if status in (429, 503):

            raise FirmsApiError(

                "Limite FIRMS atingido (5000 transacoes / 10 min). "

                "Aguarde e tente novamente."

            ) from exc

        if status == 504:

            raise FirmsApiError(

                "Timeout FIRMS (504). Reduza DAY_RANGE ou area e tente de novo."

            ) from exc

        raise FirmsApiError(f"Erro HTTP FIRMS {status}: {response.text[:200]}") from exc





def _row_to_fire_event(row: dict[str, str]) -> FireEvent | None:

    lat = _parse_float(row.get("latitude"))

    lon = _parse_float(row.get("longitude"))

    acq_date = _normalize_date(row.get("acq_date", ""))

    if lat is None or lon is None or not acq_date:

        return None



    acq_time = _optional_str(row.get("acq_time"))

    satellite = _optional_str(row.get("satellite"))

    dedup_key = _optional_str(row.get("dedup_key")) or build_dedup_key(

        lat, lon, acq_date, acq_time, satellite

    )



    return FireEvent(

        latitude=lat,

        longitude=lon,

        acq_date=acq_date,

        dedup_key=dedup_key,

        acq_time=acq_time,

        brightness=_brightness_from_row(row),

        confidence=_optional_str(row.get("confidence")),

        frp=_parse_float(row.get("frp")),

        satellite=satellite,

        instrument=_optional_str(row.get("instrument")),

        region_key=_optional_str(row.get("region_key")),

    )





def _brightness_from_row(row: dict[str, str]) -> float | None:

    """VIIRS usa bright_ti4; MODIS usa brightness."""

    return _parse_float(row.get("brightness")) or _parse_float(row.get("bright_ti4"))





def _inside_bbox(lat: float, lon: float, bbox: BBox) -> bool:

    return (

        bbox.min_lat <= lat <= bbox.max_lat

        and bbox.min_lon <= lon <= bbox.max_lon

    )





def _normalize_date(raw: str) -> str:

    value = raw.strip()

    if not value:

        return ""

    # FIRMS pode retornar YYYY-MM-DD ou YYYY-MM-DD+00:00

    return value.split("T")[0].split("+")[0][:10]





def _parse_float(value: str | None) -> float | None:

    if value is None or str(value).strip() == "":

        return None

    return float(value)





def _optional_str(value: str | None) -> str | None:

    if value is None or str(value).strip() == "":

        return None

    return str(value).strip()


