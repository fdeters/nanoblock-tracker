import csv
import sys

import pytest

import nanoblock_tracker.scraper as scraper_module
from nanoblock_scraper import main
from nanoblock_tracker.config import build_parser, resolve_config_value
from nanoblock_tracker.scraper import (
    build_summary,
    export_products,
    fetch_page,
    merge_products,
    parse_products,
)

SAMPLE_HTML = """
<table class="roundy">
  <tr><th>Code</th><th>Name</th></tr>
  <tr><td>NBPM_001</td><td>Pokémon Center RS</td></tr>
  <tr><td>NBPM_R01</td><td>Pokémon Series DX</td></tr>
  <tr><td>NBPM_036</td><td>20th Anniversary ( )</td></tr>
  <tr><td>NBPM_999</td><td>Nanoblock+ Set</td></tr>
  <tr><td>ABC123</td><td>Not a Nanoblock product</td></tr>
</table>
"""


def test_fetch_page_sends_browser_user_agent(monkeypatch) -> None:
    class DummyResponse:
        text = "page contents"
        status_code = 200

        @staticmethod
        def raise_for_status() -> None:
            pass

    requested = {}

    def mock_get(url, **kwargs):
        requested["url"] = url
        requested.update(kwargs)
        return DummyResponse()

    monkeypatch.setattr(scraper_module.requests, "get", mock_get)

    assert fetch_page("https://example.com") == "page contents"
    assert requested["url"] == "https://example.com"
    assert requested["headers"]["User-Agent"].startswith("Mozilla/5.0")


def test_fetch_page_falls_back_to_browser_on_403(monkeypatch) -> None:
    class BlockedResponse:
        status_code = 403
        text = "challenge"

        @staticmethod
        def raise_for_status() -> None:
            raise AssertionError("should not be called")

    monkeypatch.setattr(
        scraper_module.requests, "get", lambda url, **kwargs: BlockedResponse()
    )
    monkeypatch.setattr(
        scraper_module, "fetch_page_browser", lambda url: f"browser:{url}"
    )

    assert fetch_page("https://example.com") == "browser:https://example.com"


def test_parse_products_filters_and_normalizes() -> None:
    products = parse_products(SAMPLE_HTML)

    assert len(products) == 3
    assert products[0]["Product Code"] == "NBPM_001"
    assert products[0]["Product Name"] == "Pokémon Center"
    assert products[0]["Variant"] == "RS"
    assert products[0]["Collected"] == ""
    assert products[0]["Not interested"] == ""
    assert products[1]["Product Code"] == "NBPM_R01"
    assert products[1]["Product Name"] == "Pokémon Series"
    assert products[1]["Variant"] == "DX"
    assert products[2]["Product Code"] == "NBPM_036"
    assert products[2]["Product Name"] == "20th Anniversary"
    assert products[2]["Variant"] == ""


def test_build_parser_leaves_sheet_name_unset_until_explicitly_provided(
    monkeypatch,
) -> None:
    monkeypatch.setenv("GOOGLE_SHEET_NAME", "Env Sheet")

    parser = build_parser()
    args = parser.parse_args([])

    assert args.sheet_name is None


def test_resolve_config_value_falls_back_to_default(
    monkeypatch,
) -> None:
    monkeypatch.delenv("GOOGLE_SHEET_NAME", raising=False)

    assert (
        resolve_config_value(
            None,
            "GOOGLE_SHEET_NAME",
            "Sheet1",
        )
        == "Sheet1"
    )


def test_main_exits_with_error_when_sync_requested_without_credentials(
    monkeypatch,
) -> None:
    monkeypatch.delenv("GOOGLE_APPLICATION_CREDENTIALS", raising=False)
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", "")
    monkeypatch.setattr("nanoblock_scraper.fetch_page", lambda url: "<table></table>")
    monkeypatch.setattr("nanoblock_scraper.parse_products", lambda html: [])
    monkeypatch.setattr(sys, "argv", ["nanoblock_scraper.py", "--sheet-id", "sheet-id"])

    with pytest.raises(SystemExit, match="Google Sheets sync failed"):
        main()


def test_merge_products_only_appends_new_codes() -> None:
    existing_rows = [
        {
            "Product Code": "NBPM_001",
            "Product Name": "Pokémon Center",
            "Variant": "RS",
            "Collected": "yes",
            "Not interested": "",
        }
    ]
    source_products = [
        {
            "Product Code": "NBPM_001",
            "Product Name": "Pokémon Center",
            "Variant": "RS",
            "Collected": "",
            "Not interested": "",
        },
        {
            "Product Code": "NBPM_002",
            "Product Name": "Pikachu",
            "Variant": "",
            "Collected": "",
            "Not interested": "",
        },
    ]

    new_products = merge_products(source_products, existing_rows)

    assert len(new_products) == 1
    assert new_products[0]["Product Code"] == "NBPM_002"
    assert new_products[0]["Product Name"] == "Pikachu"


def test_build_summary_formats_products() -> None:
    products = [
        {
            "Product Code": "NBPM_001",
            "Product Name": "Pikachu",
            "Variant": "RS",
        },
        {
            "Product Code": "NBPM_002",
            "Product Name": "Eevee",
            "Variant": "",
        },
    ]

    summary = build_summary(products)

    assert "Added 2 new Nanoblock product(s):" in summary
    assert "NBPM_001: Pikachu (RS)" in summary
    assert "NBPM_002: Eevee" in summary


def test_export_products_writes_expected_csv(tmp_path) -> None:
    output_path = tmp_path / "products.csv"
    products = [
        {
            "Product Name": "Pikachu",
            "Product Code": "NBPM_001",
            "Variant": "RS",
            "Collected": "",
            "Not interested": "",
        }
    ]

    exported_path = export_products(products, output_path)

    assert exported_path == output_path
    with output_path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))

    assert rows[0]["Product Code"] == "NBPM_001"
    assert rows[0]["Product Name"] == "Pikachu"
