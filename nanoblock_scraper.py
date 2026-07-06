from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import List
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

DEFAULT_URL = "https://bulbapedia.bulbagarden.net/wiki/Pok%C3%A9mon_Nanoblocks"
PRODUCT_CODE_RE = re.compile(r"\bNBPM(?:_[0-9]{3}|_R[0-9]{2}|_XXX)\b", re.IGNORECASE)
VARIANT_RE = re.compile(
    r"\b(RS|DX|Extreme DX|Monotone|Translucent|Pokémon Quest|Galarian Form|Brilliant Shining|Lunar New Year Costume)\b",
    re.IGNORECASE,
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
                name = VARIANT_RE.sub("", details).strip(" -")
            else:
                name = details.strip()

            products.append(
                {
                    "product_name": name,
                    "product_code": code,
                    "variant": variant,
                }
            )

    return products


def export_products(products: List[dict], output_path: str | Path | None = None) -> Path:
    output = Path(output_path) if output_path else Path("nanoblock_products.csv")
    with output.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["product_name", "product_code", "variant"])
        writer.writeheader()
        writer.writerows(products)
    return output


def main() -> None:
    html = fetch_page()
    products = parse_products(html)
    output_path = export_products(products, "nanoblock_products.csv")
    print(f"Wrote {len(products)} products to {output_path}")


if __name__ == "__main__":
    main()
