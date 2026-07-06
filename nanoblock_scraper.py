from __future__ import annotations

import argparse
import csv
import os
import re
from pathlib import Path
from typing import Any, Dict, List, cast

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional dependency
    load_dotenv = None

import requests
from bs4 import BeautifulSoup

try:
    import gspread
    from google.oauth2.service_account import Credentials
except ImportError:  # pragma: no cover - used when optional dependency is not installed
    gspread = None
    Credentials = None

DEFAULT_URL = "https://bulbapedia.bulbagarden.net/wiki/" "Pok%C3%A9mon_Nanoblocks"
FIELDNAMES = [
    "Product Name",
    "Product Code",
    "Variant",
    "Collected",
    "Not interested",
]
PRODUCT_CODE_RE = re.compile(
    r"\bNBPM(?:_[0-9]{3}|_R[0-9]{2}|_XXX)\b",
    re.IGNORECASE,
)
VARIANT_RE = re.compile(
    r"\b(RS|DX|Extreme DX|Monotone|Translucent|Pokémon Quest|"
    r"Galarian Form|Brilliant Shining|Lunar New Year Costume)\b",
    re.IGNORECASE,
)
PARENTHETICAL_RE = re.compile(r"\s*\([^)]*\)\s*$")


def fetch_page(url: str = DEFAULT_URL) -> str:
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    return response.text


def parse_products(html: str) -> List[dict]:
    soup = BeautifulSoup(html, "html.parser")
    products: List[dict] = []

    for table in soup.select("table.roundy"):
        for row in table.select("tr"):
            cells = [cell.get_text(" ", strip=True) for cell in row.select("th, td")]
            if not cells:
                continue

            code = cells[0] if len(cells) > 0 else ""
            details = cells[1] if len(cells) > 1 else ""
            if not PRODUCT_CODE_RE.search(code):
                continue
            if re.search(r"nanoblock\+", details, flags=re.IGNORECASE):
                continue

            name = details
            variant = ""
            variant_match = VARIANT_RE.search(details)
            if variant_match:
                variant = variant_match.group(0)
                name = VARIANT_RE.sub("", details)
            else:
                name = details

            name = PARENTHETICAL_RE.sub("", name).strip(" -")

            products.append(
                {
                    "Product Name": name,
                    "Product Code": code,
                    "Variant": variant,
                    "Collected": "",
                    "Not interested": "",
                }
            )

    return products


def merge_products(
    source_products: List[dict],
    existing_rows: List[dict],
) -> List[dict]:
    existing_codes = {
        row.get("Product Code", "") for row in existing_rows if row.get("Product Code")
    }
    return [
        product
        for product in source_products
        if product.get("Product Code") not in existing_codes
    ]


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


def export_products(
    products: List[dict],
    output_path: str | Path | None = None,
) -> Path:
    output = Path(output_path) if output_path else Path("nanoblock_products.csv")
    with output.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(products)
    return output


def build_summary(products: List[dict]) -> str:
    if not products:
        return "No new Nanoblock products were added."

    lines = [f"Added {len(products)} new Nanoblock product(s):"]
    for product in products[:10]:
        code = product.get("Product Code", "")
        name = product.get("Product Name", "")
        variant = product.get("Variant", "")
        suffix = f" ({variant})" if variant else ""
        lines.append(f"- {code}: {name}{suffix}")
    if len(products) > 10:
        lines.append(f"...and {len(products) - 10} more")
    return "\n".join(lines)


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    load_environment_config(args.env_file)

    sheet_id = resolve_config_value(args.sheet_id, "GOOGLE_SHEET_ID")
    credentials_path = resolve_config_value(
        args.credentials,
        "GOOGLE_APPLICATION_CREDENTIALS",
    )
    sheet_name = (
        resolve_config_value(args.sheet_name, "GOOGLE_SHEET_NAME", "Sheet1") or "Sheet1"
    )

    html = fetch_page(args.url)
    products = parse_products(html)

    if sheet_id:
        try:
            existing_rows = read_google_sheet_rows(
                sheet_id,
                sheet_name,
                credentials_path,
            )
            new_products = merge_products(products, existing_rows)
            appended = append_google_sheet_rows(
                sheet_id,
                new_products,
                sheet_name,
                credentials_path,
            )
        except (RuntimeError, FileNotFoundError) as exc:
            raise SystemExit(f"Google Sheets sync failed: {exc}") from exc

        if appended:
            print(f"Appended {appended} new products to Google Sheet {sheet_id}")
            print(build_summary(new_products))
        else:
            print("No new products to append to Google Sheet")
    else:
        export_products(products, args.output)
        print(f"Wrote {len(products)} products to {args.output}")


if __name__ == "__main__":
    main()
