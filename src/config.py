"""Configuracao central do OrbitFire: regiao, paths e variaveis de ambiente."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# Carrega .env na raiz do projeto (se existir)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_PROJECT_ROOT / ".env")


@dataclass(frozen=True)
class BBox:
    """Retangulo geografico: lat/lon minimo e maximo (graus decimais)."""

    min_lat: float
    max_lat: float
    min_lon: float
    max_lon: float

    def as_firms_area(self) -> str:
        """Formato FIRMS API: west,south,east,north."""
        return f"{self.min_lon},{self.min_lat},{self.max_lon},{self.max_lat}"


# --- Regiao Centro-Oeste (GO, MT, MS, DF) — alinhado a docs/Escopo.md ---
REGION: str = "centro-oeste"
STATES: tuple[str, ...] = ("GO", "MT", "MS", "DF")
BBOX: BBox = BBox(min_lat=-24.1, max_lat=-12.0, min_lon=-61.6, max_lon=-45.0)

# Resolucao da grade em graus (menor = mais celulas)
GRID_DEG: float = float(os.getenv("GRID_DEG", "0.25"))

# --- Paths de dados ---
PROJECT_ROOT: Path = _PROJECT_ROOT
DATA_DIR: Path = PROJECT_ROOT / "data"
DATA_RAW: Path = DATA_DIR / "raw"
DATA_PROCESSED: Path = DATA_DIR / "processed"
DATA_SEED: Path = DATA_DIR / "seed"
DATA_MODELS: Path = DATA_DIR / "models"

# SQLite da POC
DB_PATH: Path = DATA_DIR / "orbitfire.db"
DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{DB_PATH.as_posix()}")

# --- NASA FIRMS ---
FIRMS_MAP_KEY: str = os.getenv("FIRMS_MAP_KEY", "")
FIRMS_BASE_URL: str = "https://firms.modaps.eosdis.nasa.gov/api"
FIRMS_SOURCE: str = os.getenv("FIRMS_SOURCE", "VIIRS_SNPP_NRT")
FIRMS_DAYS: int = int(os.getenv("FIRMS_DAYS", "7"))
FIRMS_BBOX: BBox = BBOX

# --- Clima (Open-Meteo por padrao na POC) ---
OPEN_METEO_URL: str = "https://archive-api.open-meteo.com/v1/archive"

# --- Execucao ---
OFFLINE_MODE: bool = os.getenv("OFFLINE_MODE", "0").strip().lower() in (
    "1",
    "true",
    "yes",
)
API_HOST: str = os.getenv("API_HOST", "127.0.0.1")
API_PORT: int = int(os.getenv("API_PORT", "8000"))

# Janela de dias usada no treino e ingestao historica
RECENT_DAYS: int = int(os.getenv("RECENT_DAYS", "90"))


def ensure_data_dirs() -> None:
    """Garante que pastas de dados existem antes de ETL ou persistencia."""
    for path in (DATA_RAW, DATA_PROCESSED, DATA_SEED, DATA_MODELS):
        path.mkdir(parents=True, exist_ok=True)


def is_firms_configured() -> bool:
    """True quando ha chave FIRMS ou modo offline ativo."""
    return OFFLINE_MODE or bool(FIRMS_MAP_KEY.strip())
