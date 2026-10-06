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
        help=(
            "Write a local CSV export instead of updating Google Sheets. "
            "A bare file name is written to the output/ folder"
        ),
    )
    parser.add_argument(
        "--challenge-timeout",
        type=float,
        default=None,
        metavar="SECONDS",
        help=(
            "Seconds the browser fallback waits for the Cloudflare challenge "
            "to clear (default: 20). Use a larger value for unattended runs"
        ),
    )
    parser.add_argument(
        "--sheet-id",
        help="Google Sheets spreadsheet ID to update",
    )
    parser.add_argument(
        "--worksheet-name",
        help="Worksheet (tab) name to update; defaults to GOOGLE_WORKSHEET_NAME or 'pokemon'",
    )
    parser.add_argument(
        "--credentials",
        help="Path to the Google service account credentials JSON file or a raw JSON string",
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
