from __future__ import annotations

import argparse
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional dependency
    load_dotenv = None

from .constants import DEFAULT_URL


def load_environment_config(env_path: str | None = None) -> None:
    if load_dotenv is None:
        return
    env_path_obj = Path(env_path) if env_path else Path(".env")
    if env_path_obj.exists():
        load_dotenv(env_path_obj, override=False)


def resolve_config_value(
    cli_value: str | None,
    env_key: str,
    default: str | None = None,
) -> str | None:
    if cli_value is not None:
        return cli_value
    return os.getenv(env_key, default)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Scrape Nanoblock products and optionally sync them to Google " "Sheets"
        )
    )
    parser.add_argument("--url", default=DEFAULT_URL, help="Source page URL")
    parser.add_argument(
        "--output",
        default="nanoblock_products.csv",
        help="Where to write the local CSV export",
    )
    parser.add_argument(
        "--sheet-id",
        help="Google Sheets spreadsheet ID to update",
    )
    parser.add_argument(
        "--sheet-name",
        help="Worksheet name to update",
    )
    parser.add_argument(
        "--credentials",
        help="Path to the Google service account credentials JSON file",
    )
    parser.add_argument(
        "--env-file",
        default=".env",
        help=(
            "Path to a .env file containing GOOGLE_SHEET_ID and "
            "GOOGLE_APPLICATION_CREDENTIALS"
        ),
    )
    return parser
