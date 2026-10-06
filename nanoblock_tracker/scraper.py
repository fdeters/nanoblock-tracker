from __future__ import annotations

import csv
import re
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from .constants import (
    DEFAULT_URL,
    FIELDNAMES,
    PARENTHETICAL_RE,
    PRODUCT_CODE_RE,
    VARIANT_RE,
)

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

CHALLENGE_TITLE = "Just a moment..."
BROWSER_TIMEOUT_MS = 60_000


def fetch_page_browser(url: str = DEFAULT_URL, headless: bool = False) -> str:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=headless)
        try:
            page = browser.new_page(user_agent=USER_AGENT)
            response = page.goto(url, timeout=BROWSER_TIMEOUT_MS)
            if page.title() == CHALLENGE_TITLE or (response and response.status == 403):
                page.wait_for_function(
                    "title => document.title !== title",
                    arg=CHALLENGE_TITLE,
                    timeout=BROWSER_TIMEOUT_MS,
                )
                page.wait_for_load_state("load")
            return page.content()
        finally:
            browser.close()


def fetch_page(url: str = DEFAULT_URL) -> str:
    response = requests.get(
        url,
        headers={"User-Agent": USER_AGENT},
        timeout=30,
    )
    if response.status_code == 403:
        return fetch_page_browser(url)
    response.raise_for_status()
    return response.text


def parse_products(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    products: list[dict] = []

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
    source_products: list[dict],
    existing_rows: list[dict],
) -> list[dict]:
    existing_codes = {
        row.get("Product Code", "") for row in existing_rows if row.get("Product Code")
    }
    return [
        product
        for product in source_products
        if product.get("Product Code") not in existing_codes
    ]


def export_products(
    products: list[dict],
    output_path: str | Path | None = None,
) -> Path:
    output = Path(output_path) if output_path else Path("nanoblock_products.csv")
    with output.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(products)
    return output


def build_summary(products: list[dict]) -> str:
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
