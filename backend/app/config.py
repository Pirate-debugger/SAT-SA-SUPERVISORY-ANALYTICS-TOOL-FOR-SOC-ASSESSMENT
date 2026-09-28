import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR.parent / "data"
UPLOADS_DIR = DATA_DIR / "uploads"
SYNTHETIC_DIR = DATA_DIR / "synthetic"
DATABASE_URL = f"sqlite:///{BASE_DIR / 'sat_sa.db'}"

# Ensure directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
SYNTHETIC_DIR.mkdir(parents=True, exist_ok=True)

APP_NAME = "SAT-SA: Supervisory Analytics Tool for SOC Assessment"
APP_VERSION = "0.1.0-phase1"
RULESET_VERSION = "ruleset-v1.0.0-offline"
ANALYTICS_VERSION = "analytics-v1.0.0-baseline"
