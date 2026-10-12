from __future__ import annotations

import os
from pathlib import Path
from typing import Dict

BASE_DIR = Path(__file__).resolve().parents[3]
BACKEND_DIR = BASE_DIR / "backend"

APP_NAME = "Smart Placement Readiness Analyser"
APP_VERSION = "1.0.0"
SCORING_MODEL_VERSION = "1.0.0"
QUESTION_BANK_VERSION = "1.0.0"

MODEL_DIR = BASE_DIR / "ml" / "models"
MODEL_PATH = Path(os.getenv("MODEL_PATH", str(MODEL_DIR / "url_classifier.joblib")))
MODEL_SCHEMA_VERSION = "1.0"
DEFAULT_FALLBACK_MODE = "rule-based"

BACKEND_HOST = os.getenv("BACKEND_HOST", "0.0.0.0")
BACKEND_PORT = int(os.getenv("BACKEND_PORT", "8000"))
ENABLE_HISTORY = os.getenv("ENABLE_HISTORY", "true").lower() == "true"
MAX_URL_LENGTH = 2048

DATA_DIR = BACKEND_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = Path(os.getenv("PLACEMENT_DB_PATH", str(DATA_DIR / "placement_readiness.db")))
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DB_PATH}")

SECRET_KEY = os.getenv("SECRET_KEY", "dev-local-placement-secret-key-change-in-prod-2026")
TOKEN_EXPIRE_HOURS = int(os.getenv("TOKEN_EXPIRE_HOURS", "24"))
ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "ALLOWED_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000",
    ).split(",")
    if origin.strip()
]

AI_PROVIDER_ENABLED = os.getenv("AI_PROVIDER_ENABLED", "false").lower() == "true"
AI_API_KEY = os.getenv("AI_API_KEY", "")
AI_TIMEOUT_SECONDS = float(os.getenv("AI_TIMEOUT_SECONDS", "5.0"))

READINESS_THRESHOLDS: Dict[str, float] = {
    "needs_more_preparation": 45.0,
    "developing": 65.0,
    "progressing_well": 80.0,
}

MAX_ATTEMPTS_RETENTION_PER_ASSESSMENT = int(os.getenv("MAX_ATTEMPTS_RETENTION", "50"))

DISCLAIMER_TEXT = (
    "Placement readiness scores and categories are educational preparation guidance based solely on "
    "completed assessment items. They do not predict hiring outcomes, guarantee employment, or "
    "represent a company's recruitment criteria."
)

