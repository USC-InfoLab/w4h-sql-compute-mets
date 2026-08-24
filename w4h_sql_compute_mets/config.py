"""Load W4H_API_KEY and related settings from environment / .env (never committed)."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

_PKG_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_PKG_ROOT / ".env")


def require_api_key() -> str:
    key = os.environ.get("W4H_API_KEY", "").strip()
    if not key:
        raise RuntimeError(
            "Set W4H_API_KEY in your environment or .env (copy .env.example). "
            "Generate from W4H Profile → API keys."
        )
    return key


def api_base() -> str:
    return os.environ.get("W4H_API_BASE", "http://localhost:2026").rstrip("/")


def dataset_id() -> str:
    return os.environ.get("W4H_DATASET_ID", "").strip()


def project_id() -> str:
    return os.environ.get("W4H_PROJECT_ID", "").strip()


def contribution_slug() -> str:
    return os.environ.get("W4H_SQL_CONTRIBUTION_SLUG", "w4h-sql-compute-mets").strip()
