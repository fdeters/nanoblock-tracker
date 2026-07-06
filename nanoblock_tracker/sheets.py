from __future__ import annotations

import os
from typing import Any, Dict, List, cast

try:
    import gspread
    from google.oauth2.service_account import Credentials
except ImportError:  # pragma: no cover - used when optional dependency is not installed
    gspread = None
    Credentials = None

from .constants import FIELDNAMES


def normalize_sheet_row(row: Dict[str, Any]) -> Dict[str, Any]:
    return {field: row.get(field, "") for field in FIELDNAMES}


def read_google_sheet_rows(
    spreadsheet_id: str,
    sheet_name: str = "Sheet1",
    credentials_path: str | None = None,
) -> List[Dict[str, Any]]:
    if gspread is None or Credentials is None:
        raise RuntimeError(
            "gspread and google-auth are required for Google Sheets sync"
        )

    credentials_path = credentials_path or os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if not credentials_path:
        raise RuntimeError(
            "Provide --credentials or set GOOGLE_APPLICATION_CREDENTIALS"
        )

    try:
        credentials = Credentials.from_service_account_file(
            credentials_path,
            scopes=["https://www.googleapis.com/auth/spreadsheets"],
        )
        client = gspread.authorize(credentials)
        worksheet = client.open_by_key(spreadsheet_id).worksheet(sheet_name)
    except FileNotFoundError as exc:
        raise RuntimeError(
            f"Google Sheets sync failed: credentials file not found at {credentials_path}"
        ) from exc
    except Exception as exc:  # pragma: no cover - defensive for runtime failures
        raise RuntimeError(f"Google Sheets sync failed: {exc}") from exc

    rows = worksheet.get_all_records()
    return [normalize_sheet_row(row) for row in rows]


def append_google_sheet_rows(
    spreadsheet_id: str,
    products: List[Dict[str, Any]],
    sheet_name: str = "Sheet1",
    credentials_path: str | None = None,
) -> int:
    if not products:
        return 0

    if gspread is None or Credentials is None:
        raise RuntimeError(
            "gspread and google-auth are required for Google Sheets sync"
        )

    credentials_path = credentials_path or os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if not credentials_path:
        raise RuntimeError(
            "Provide --credentials or set GOOGLE_APPLICATION_CREDENTIALS"
        )

    try:
        credentials = Credentials.from_service_account_file(
            credentials_path,
            scopes=["https://www.googleapis.com/auth/spreadsheets"],
        )
        client = gspread.authorize(credentials)
        worksheet = client.open_by_key(spreadsheet_id).worksheet(sheet_name)
    except FileNotFoundError as exc:
        raise RuntimeError(
            f"Google Sheets sync failed: credentials file not found at {credentials_path}"
        ) from exc
    except Exception as exc:  # pragma: no cover - defensive for runtime failures
        raise RuntimeError(f"Google Sheets sync failed: {exc}") from exc

    rows = [[product.get(field, "") for field in FIELDNAMES] for product in products]
    worksheet.append_rows(
        rows,
        value_input_option=cast(Any, "USER_ENTERED"),
    )
    return len(products)
