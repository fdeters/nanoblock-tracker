from __future__ import annotations

import json
import os
from typing import Any, cast

try:
    import gspread
    from google.oauth2.service_account import Credentials
    from gspread.utils import rowcol_to_a1
except ImportError:  # pragma: no cover - used when optional dependency is not installed
    gspread = None
    Credentials = None
    rowcol_to_a1 = None

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

    headers = worksheet.row_values(1) or FIELDNAMES
    rows = [[product.get(field, "") for field in headers] for product in products]
    worksheet.append_rows(
        rows,
        value_input_option=cast(Any, "USER_ENTERED"),
    )
    return len(products)


def update_google_sheet_release_dates(
    spreadsheet_id: str,
    products: list[dict[str, Any]],
    existing_rows: list[dict[str, Any]],
    worksheet_name: str = DEFAULT_WORKSHEET_NAME,
    credentials_path: str | None = None,
) -> int:
    row_numbers = {
        row.get("Product Code"): index + 2
        for index, row in enumerate(existing_rows)
        if row.get("Product Code")
    }
    existing_by_code = {
        row.get("Product Code"): row for row in existing_rows if row.get("Product Code")
    }
    updates = [
        (row_numbers[product["Product Code"]], product.get("Release Date", ""))
        for product in products
        if product.get("Product Code") in existing_by_code
        and not str(
            existing_by_code[product["Product Code"]].get("Release Date") or ""
        ).strip()
        and str(product.get("Release Date") or "").strip()
    ]
    if not updates:
        return 0

    if gspread is None or Credentials is None or rowcol_to_a1 is None:
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

    headers = worksheet.row_values(1)
    if "Release Date" not in headers:
        raise RuntimeError("Google Sheets sync failed: 'Release Date' column not found")

    release_date_column = headers.index("Release Date") + 1
    worksheet.batch_update(
        [
            {
                "range": cast(Any, rowcol_to_a1)(row_number, release_date_column),
                "values": [[release_date]],
            }
            for row_number, release_date in updates
        ],
        value_input_option=cast(Any, "USER_ENTERED"),
    )
    return len(updates)
