from pathlib import Path
import os

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"

load_dotenv(BASE_DIR / ".env")


class Config:
    SECRET_KEY = os.getenv("PHARMAPATH_SECRET_KEY", "development-secret")
    DATABASE_PATH = os.getenv("PHARMAPATH_DATABASE_PATH", str(DATA_DIR / "pharmapath.db"))
    GRAPH_CACHE_PATH = os.getenv(
        "PHARMAPATH_GRAPH_CACHE_PATH",
        str(DATA_DIR / "cache" / "drug_graph.json"),
    )
    DRUG_FIXTURE_PATH = os.getenv(
        "PHARMAPATH_DRUG_FIXTURE_PATH",
        str(DATA_DIR / "seed" / "drug_catalog.json"),
    )
    INDIA_MEDICINE_CATALOG_PATH = os.getenv(
        "PHARMAPATH_INDIA_MEDICINE_CATALOG_PATH",
        str(DATA_DIR / "seed" / "india_medicine_catalog.json"),
    )
    OPENFDA_API_KEY = os.getenv("OPENFDA_API_KEY", "")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY", "")
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
