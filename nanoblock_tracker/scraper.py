from __future__ import annotations

import csv
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote, urlparse

import requests
from bs4 import BeautifulSoup
from playwright.sync_api import Error as PlaywrightError

from .constants import (
    DEFAULT_OUTPUT_DIR,
    DEFAULT_OUTPUT_NAME,
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

BROWSER_TIMEOUT_MS = 20_000
WAYBACK_ATTEMPTS = 3
WAYBACK_BACKOFF_SECONDS = (5, 15)
WAYBACK_MAX_RETRY_AFTER_SECONDS = 60
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
WAYBACK_TIMESTAMP_RE = re.compile(r"/web/(\d{4})(\d{2})(\d{2})")
RELEASE_DATE_RE = re.compile(
    r"\b(?:"
    r"\d{4}-\d{1,2}-\d{1,2}|"
    r"[A-Z][a-z]+ \d{1,2},? \d{4}|"
    r"\d{1,2} [A-Z][a-z]+ \d{4}|"
    r"[A-Z][a-z]+ \d{4}"
    r")\b"
)
BROWSER_PROFILE_DIR = Path(".browser-profile")
WAYBACK_URL = "https://web.archive.org/web/2id_/"
CONTENT_SELECTOR = "table.roundy"


def _launch_context(playwright, headless: bool):
    options = {
        "user_data_dir": str(BROWSER_PROFILE_DIR),
        "headless": headless,
        "chromium_sandbox": True,
        "user_agent": USER_AGENT,
    }
    try:
        return playwright.chromium.launch_persistent_context(
            channel="chrome", **options
        )
    except PlaywrightError:
        return playwright.chromium.launch_persistent_context(**options)


def fetch_page_browser(
    url: str = DEFAULT_URL,
    headless: bool = False,
    timeout_ms: int = BROWSER_TIMEOUT_MS,
) -> str:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        context = _launch_context(playwright, headless)
        try:
            context.add_init_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )
            page = context.pages[0] if context.pages else context.new_page()
            page.goto(url, timeout=timeout_ms)
            # A persistent profile keeps Cloudflare clearance cookies between
            # runs; if a checkbox challenge appears, solve it in the window.
            page.wait_for_selector(
                CONTENT_SELECTOR, state="attached", timeout=timeout_ms
            )
            return page.content()
        finally:
            context.close()


def _log(message: str) -> None:
    print(f"[fetch] {message}")


def _has_products_table(html: str) -> bool:
    return BeautifulSoup(html, "html.parser").select_one(CONTENT_SELECTOR) is not None


def fetch_page_impersonated(url: str = DEFAULT_URL) -> str | None:
    from curl_cffi import requests as curl_requests

    try:
        response = curl_requests.get(url, impersonate="chrome", timeout=30)
    except curl_requests.RequestsError as error:
        _log(f"impersonated client failed: {error}")
        return None
    if response.status_code != 200:
        _log(f"impersonated client got HTTP {response.status_code}")
        return None
    if not _has_products_table(response.text):
        _log("impersonated client response had no products table")
        return None
    return response.text


def _retry_delay(response, attempt: int) -> float:
    retry_after = response.headers.get("Retry-After", "")
    if retry_after.isdigit():
        return min(int(retry_after), WAYBACK_MAX_RETRY_AFTER_SECONDS)
    return WAYBACK_BACKOFF_SECONDS[min(attempt, len(WAYBACK_BACKOFF_SECONDS) - 1)]


def _snapshot_date(response) -> str | None:
    match = WAYBACK_TIMESTAMP_RE.search(str(getattr(response, "url", "")))
    if not match:
        return None
    return "-".join(match.groups())


def fetch_page_archive(url: str = DEFAULT_URL) -> str | None:
    for attempt in range(WAYBACK_ATTEMPTS):
        try:
            response = requests.get(
                WAYBACK_URL + url, headers={"User-Agent": USER_AGENT}, timeout=60
            )
        except requests.RequestException as error:
            _log(f"Wayback Machine request failed: {error}")
            return None
        if response.status_code in RETRYABLE_STATUS_CODES:
            if attempt + 1 == WAYBACK_ATTEMPTS:
                _log(f"Wayback Machine got HTTP {response.status_code}; giving up")
                return None
            delay = _retry_delay(response, attempt)
            _log(
                f"Wayback Machine got HTTP {response.status_code}; "
                f"retrying in {delay:g}s (attempt {attempt + 2}/{WAYBACK_ATTEMPTS})"
            )
            time.sleep(delay)
            continue
        if not response.ok:
            _log(f"Wayback Machine got HTTP {response.status_code}")
            return None
        if not _has_products_table(response.text):
            _log("Wayback Machine response had no products table")
            return None
        snapshot = _snapshot_date(response)
        _log(f"Wayback Machine snapshot date: {snapshot or 'unknown'}")
        return response.text
    return None


def fetch_page_api(url: str = DEFAULT_URL) -> str | None:
    parsed = urlparse(url)
    if not parsed.path.startswith("/wiki/"):
        _log("MediaWiki API skipped: not a /wiki/ URL")
        return None
    api_url = f"{parsed.scheme}://{parsed.netloc}/w/api.php"
    try:
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
    except requests.RequestException as error:
        _log(f"MediaWiki API request failed: {error}")
        return None
    if not response.ok:
        _log(f"MediaWiki API got HTTP {response.status_code}")
        return None
    try:
        return response.json()["parse"]["text"]
    except (ValueError, KeyError, TypeError):
        _log("MediaWiki API response had no page text")
        return None


def _fetch_page_browser_logged(
    url: str, timeout_ms: int = BROWSER_TIMEOUT_MS
) -> str | None:
    try:
        return fetch_page_browser(url, timeout_ms=timeout_ms)
    except PlaywrightError as error:
        _log(f"browser failed: {str(error).splitlines()[0]}")
        return None


def fetch_page(url: str = DEFAULT_URL, challenge_timeout: float | None = None) -> str:
    response = requests.get(
        url,
        headers={"User-Agent": USER_AGENT},
        timeout=30,
    )
    if response.status_code != 403:
        response.raise_for_status()
        return response.text

    _log("direct request blocked (HTTP 403); trying fallbacks")
    timeout_ms = (
        int(challenge_timeout * 1000) if challenge_timeout else BROWSER_TIMEOUT_MS
    )
    methods = (
        ("impersonated client", fetch_page_impersonated),
        ("MediaWiki API", fetch_page_api),
        ("browser", lambda u: _fetch_page_browser_logged(u, timeout_ms=timeout_ms)),
        ("Wayback Machine copy (may be stale)", fetch_page_archive),
    )
    for name, fetch in methods:
        _log(f"trying {name}")
        html = fetch(url)
        if html:
            _log(f"{name} succeeded")
            return html
        _log(f"{name} did not return a page")
    raise RuntimeError("All fetch methods were blocked; see [fetch] messages above")


def _parse_release_date(value: str) -> str:
    match = RELEASE_DATE_RE.search(value)
    if not match:
        return ""

    for date_format in (
        "%Y-%m-%d",
        "%B %d, %Y",
        "%B %d %Y",
        "%d %B %Y",
        "%B %Y",
    ):
        try:
            return (
                datetime.strptime(match.group(), date_format)
                .replace(tzinfo=timezone.utc)
                .date()
                .isoformat()
            )
        except ValueError:
            continue
    return ""


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
            release_date = _parse_release_date(cells[2]) if len(cells) > 2 else ""
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
                    "Release Date": release_date,
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


def resolve_output_path(output_path: str | Path | None = None) -> Path:
    output = Path(output_path) if output_path else Path(DEFAULT_OUTPUT_NAME)
    if output.parent == Path("."):
        output = Path(DEFAULT_OUTPUT_DIR) / output
    return output


def export_products(
    products: list[dict],
    output_path: str | Path | None = None,
) -> Path:
    output = resolve_output_path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
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
