from __future__ import annotations

import json
import os
from typing import Any, cast

try:
    import gspread
    from google.oauth2.service_account import Credentials
except ImportError:  # pragma: no cover - used when optional dependency is not installed
    gspread = None
    Credentials = None

from .constants import DEFAULT_WORKSHEET_NAME, FIELDNAMES


def build_credentials(credentials_value: str | None) -> Any:
    if not credentials_value:
        raise RuntimeError(
            "Provide --credentials or set GOOGLE_APPLICATION_CREDENTIALS"
        )

    if Credentials is None:
        raise RuntimeError(
            "gspread and google-auth are required for Google Sheets sync"
        )

    try:
        if credentials_value.strip().startswith("{"):
            credentials_info = json.loads(credentials_value)
            return Credentials.from_service_account_info(
                credentials_info,
                scopes=["https://www.googleapis.com/auth/spreadsheets"],
            )

        return Credentials.from_service_account_file(
            credentials_value,
            scopes=["https://www.googleapis.com/auth/spreadsheets"],
        )
    except FileNotFoundError as exc:
        raise RuntimeError(f"credentials file not found: {credentials_value}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError("credentials JSON is invalid") from exc
    except Exception as exc:  # pragma: no cover - defensive for runtime failures
        raise RuntimeError(str(exc)) from exc


def _describe_sheets_error(exc: Exception, worksheet_name: str) -> str:
    not_found = getattr(gspread, "WorksheetNotFound", None)
    if not_found is not None and isinstance(exc, not_found):
        return (
            f"Google Sheets sync failed: worksheet '{worksheet_name}' not found. "
            "Set --worksheet-name or GOOGLE_WORKSHEET_NAME to the tab's name."
        )
    return f"Google Sheets sync failed: {exc}"


def normalize_sheet_row(row: dict[str, Any]) -> dict[str, Any]:
    return {field: row.get(field, "") for field in FIELDNAMES}


def read_google_sheet_rows(
    spreadsheet_id: str,
    worksheet_name: str = DEFAULT_WORKSHEET_NAME,
    credentials_path: str | None = None,
) -> list[dict[str, Any]]:
    if gspread is None or Credentials is None:
        raise RuntimeError(
            "gspread and google-auth are required for Google Sheets sync"
        )

    credentials_path = credentials_path or os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    try:
        credentials = build_credentials(credentials_path)
        client = gspread.authorize(credentials)
        worksheet = client.open_by_key(spreadsheet_id).worksheet(worksheet_name)
    except Exception as exc:  # pragma: no cover - defensive for runtime failures
        raise RuntimeError(_describe_sheets_error(exc, worksheet_name)) from exc

    rows = worksheet.get_all_records()
    return [normalize_sheet_row(row) for row in rows]


def append_google_sheet_rows(
    spreadsheet_id: str,
    products: list[dict[str, Any]],
    worksheet_name: str = DEFAULT_WORKSHEET_NAME,
    credentials_path: str | None = None,
) -> int:
    if not products:
        return 0

    if gspread is None or Credentials is None:
        raise RuntimeError(
            "gspread and google-auth are required for Google Sheets sync"
        )

    credentials_path = credentials_path or os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    try:
        credentials = build_credentials(credentials_path)
        client = gspread.authorize(credentials)
        worksheet = client.open_by_key(spreadsheet_id).worksheet(worksheet_name)
    except Exception as exc:  # pragma: no cover - defensive for runtime failures
        raise RuntimeError(_describe_sheets_error(exc, worksheet_name)) from exc

    rows = [[product.get(field, "") for field in FIELDNAMES] for product in products]
    worksheet.append_rows(
        rows,
        value_input_option=cast(Any, "USER_ENTERED"),
    )
    return len(products)
