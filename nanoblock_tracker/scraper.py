from __future__ import annotations

import csv
import re
from pathlib import Path
from urllib.parse import unquote, urlparse

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

BROWSER_TIMEOUT_MS = 60_000


BROWSER_ARGS = ["--disable-blink-features=AutomationControlled"]
CONTENT_SELECTOR = "table.roundy"


def _launch_browser(playwright, headless: bool):
    from playwright.sync_api import Error as PlaywrightError

    try:
        return playwright.chromium.launch(
            channel="chrome", headless=headless, args=BROWSER_ARGS
        )
    except PlaywrightError:
        return playwright.chromium.launch(headless=headless, args=BROWSER_ARGS)


def fetch_page_browser(url: str = DEFAULT_URL, headless: bool = False) -> str:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        browser = _launch_browser(playwright, headless)
        try:
            context = browser.new_context(user_agent=USER_AGENT)
            context.add_init_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )
            page = context.new_page()
            page.goto(url, timeout=BROWSER_TIMEOUT_MS)
            page.wait_for_selector(
                CONTENT_SELECTOR, state="attached", timeout=BROWSER_TIMEOUT_MS
            )
            return page.content()
        finally:
            browser.close()


def fetch_page_api(url: str = DEFAULT_URL) -> str | None:
    parsed = urlparse(url)
    if not parsed.path.startswith("/wiki/"):
        return None
    api_url = f"{parsed.scheme}://{parsed.netloc}/w/api.php"
    response = requests.get(
        api_url,
        params={
            "action": "parse",
            "page": unquote(parsed.path[len("/wiki/") :]),
            "prop": "text",
            "format": "json",
            "formatversion": "2",
        },
        headers={"User-Agent": USER_AGENT},
        timeout=30,
    )
    if not response.ok:
        return None
    try:
        return response.json()["parse"]["text"]
    except (ValueError, KeyError, TypeError):
        return None


def fetch_page(url: str = DEFAULT_URL) -> str:
    response = requests.get(
        url,
        headers={"User-Agent": USER_AGENT},
        timeout=30,
    )
    if response.status_code == 403:
        html = fetch_page_api(url)
        if html:
            return html
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
