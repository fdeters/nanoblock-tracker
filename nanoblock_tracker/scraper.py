from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import List

import requests
from bs4 import BeautifulSoup

from .constants import (
    DEFAULT_URL,
    FIELDNAMES,
    PARENTHETICAL_RE,
    PRODUCT_CODE_RE,
    VARIANT_RE,
)


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
