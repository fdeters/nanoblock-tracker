import csv
import sys
from pathlib import Path

import pytest

import nanoblock_tracker.scraper as scraper_module
from nanoblock_scraper import main
from nanoblock_tracker.config import build_parser, resolve_config_value
from nanoblock_tracker.scraper import (
    build_summary,
    export_products,
    fetch_page,
    fetch_page_archive,
    merge_products,
    parse_products,
    resolve_output_path,
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
    monkeypatch.setattr(scraper_module, "fetch_page_impersonated", lambda url: None)
    monkeypatch.setattr(scraper_module, "fetch_page_api", lambda url: None)
    monkeypatch.setattr(
        scraper_module, "fetch_page_browser", lambda url, **kwargs: f"browser:{url}"
    )

    assert fetch_page("https://example.com") == "browser:https://example.com"


def test_fetch_page_falls_back_to_api_on_403(monkeypatch) -> None:
    class Blocked:
        status_code = 403

    class ApiResponse:
        ok = True

        @staticmethod
        def json() -> dict:
            return {"parse": {"text": "<table class='roundy'></table>"}}

    calls = []

    def fake_get(url, **kwargs):
        calls.append((url, kwargs.get("params")))
        return ApiResponse() if "api.php" in url else Blocked()

    monkeypatch.setattr(scraper_module.requests, "get", fake_get)
    monkeypatch.setattr(scraper_module, "fetch_page_impersonated", lambda url: None)
    monkeypatch.setattr(
        scraper_module,
        "fetch_page_browser",
        lambda url, **kwargs: (_ for _ in ()).throw(AssertionError("no browser")),
    )

    html = fetch_page("https://example.com/wiki/Pok%C3%A9mon_Nanoblocks")

    assert html == "<table class='roundy'></table>"
    assert calls[1][0] == "https://example.com/w/api.php"
    assert calls[1][1]["page"] == "Pokémon_Nanoblocks"


def _blocked(monkeypatch) -> None:
    class Blocked:
        status_code = 403
        ok = False

    monkeypatch.setattr(scraper_module.requests, "get", lambda url, **kwargs: Blocked())


def test_fetch_page_uses_impersonated_client_on_403(monkeypatch) -> None:
    _blocked(monkeypatch)
    monkeypatch.setattr(
        scraper_module, "fetch_page_impersonated", lambda url: "impersonated"
    )

    assert fetch_page("https://example.com/wiki/X") == "impersonated"


def test_fetch_page_falls_back_to_archive_when_browser_fails(monkeypatch) -> None:
    _blocked(monkeypatch)
    monkeypatch.setattr(scraper_module, "fetch_page_impersonated", lambda url: None)
    monkeypatch.setattr(scraper_module, "fetch_page_api", lambda url: None)

    def fail(url, **kwargs):
        raise scraper_module.PlaywrightError("timeout")

    monkeypatch.setattr(scraper_module, "fetch_page_browser", fail)
    monkeypatch.setattr(scraper_module, "fetch_page_archive", lambda url: "archived")

    assert fetch_page("https://example.com/wiki/X") == "archived"


def test_fetch_page_archive_accepts_real_html(monkeypatch) -> None:
    class Archived:
        ok = True
        status_code = 200
        text = '<html><table class="roundy"><tr><td>x</td></tr></table></html>'

    monkeypatch.setattr(
        scraper_module.requests, "get", lambda url, **kwargs: Archived()
    )

    assert fetch_page_archive("https://example.com/wiki/X") == Archived.text


def test_fetch_page_logs_each_method(monkeypatch, capsys) -> None:
    _blocked(monkeypatch)
    monkeypatch.setattr(scraper_module, "fetch_page_impersonated", lambda url: None)
    monkeypatch.setattr(scraper_module, "fetch_page_api", lambda url: None)
    monkeypatch.setattr(
        scraper_module, "fetch_page_browser", lambda url, **kwargs: "page"
    )

    assert fetch_page("https://example.com/wiki/X") == "page"
    out = capsys.readouterr().out
    assert "impersonated client did not return a page" in out
    assert "browser succeeded" in out


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


def test_build_parser_leaves_worksheet_name_unset_until_explicitly_provided(
    monkeypatch,
) -> None:
    monkeypatch.setenv("GOOGLE_WORKSHEET_NAME", "Env Sheet")

    parser = build_parser()
    args = parser.parse_args([])

    assert args.worksheet_name is None


def test_resolve_config_value_falls_back_to_default(
    monkeypatch,
) -> None:
    monkeypatch.delenv("GOOGLE_WORKSHEET_NAME", raising=False)

    assert (
        resolve_config_value(
            None,
            "GOOGLE_WORKSHEET_NAME",
            "pokemon",
        )
        == "pokemon"
    )


def test_main_exits_with_error_when_sync_requested_without_credentials(
    monkeypatch,
) -> None:
    monkeypatch.delenv("GOOGLE_APPLICATION_CREDENTIALS", raising=False)
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", "")
    monkeypatch.setattr(
        "nanoblock_scraper.fetch_page", lambda url, timeout: "<table></table>"
    )
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


def test_resolve_output_path_puts_bare_names_in_output_folder() -> None:
    assert resolve_output_path("test.csv") == Path("output") / "test.csv"
    assert resolve_output_path(None) == Path("output") / "nanoblock_products.csv"
    assert resolve_output_path("exports/a.csv") == Path("exports") / "a.csv"


def test_main_with_output_skips_google_sheets(monkeypatch, tmp_path, capsys) -> None:
    out = tmp_path / "test.csv"
    monkeypatch.setattr(
        "nanoblock_scraper.fetch_page", lambda url, timeout: "<table></table>"
    )
    monkeypatch.setattr("nanoblock_scraper.parse_products", lambda html: [])

    def fail(*args, **kwargs):
        raise AssertionError("Google Sheets should not be touched")

    monkeypatch.setattr("nanoblock_scraper.read_google_sheet_rows", fail)
    monkeypatch.setattr(
        sys,
        "argv",
        ["nanoblock_scraper.py", "--sheet-id", "sheet-id", "--output", str(out)],
    )

    main()

    assert out.exists()
    assert "skipping the Google Sheets update" in capsys.readouterr().out


class _ArchiveResponse:
    def __init__(self, status_code, text="", headers=None, url="") -> None:
        self.status_code = status_code
        self.ok = status_code < 400
        self.text = text
        self.headers = headers or {}
        self.url = url


def test_fetch_page_archive_retries_on_429_and_logs_snapshot_date(
    monkeypatch, capsys
) -> None:
    html = '<table class="roundy"><tr><td>x</td></tr></table>'
    responses = iter(
        [
            _ArchiveResponse(429, headers={"Retry-After": "2"}),
            _ArchiveResponse(
                200, html, url="https://web.archive.org/web/20250102030405id_/x"
            ),
        ]
    )
    sleeps: list[float] = []
    monkeypatch.setattr(
        scraper_module.requests, "get", lambda url, **kwargs: next(responses)
    )
    monkeypatch.setattr(scraper_module.time, "sleep", sleeps.append)

    assert fetch_page_archive("https://example.com/wiki/X") == html
    assert sleeps == [2]
    assert "snapshot date: 2025-01-02" in capsys.readouterr().out


def test_fetch_page_archive_gives_up_after_bounded_attempts(monkeypatch) -> None:
    calls: list[str] = []

    def fake_get(url, **kwargs):
        calls.append(url)
        return _ArchiveResponse(429)

    sleeps: list[float] = []
    monkeypatch.setattr(scraper_module.requests, "get", fake_get)
    monkeypatch.setattr(scraper_module.time, "sleep", sleeps.append)

    assert fetch_page_archive("https://example.com/wiki/X") is None
    assert len(calls) == scraper_module.WAYBACK_ATTEMPTS
    assert sleeps == [5, 15]


def test_fetch_page_passes_challenge_timeout_to_browser(monkeypatch) -> None:
    _blocked(monkeypatch)
    monkeypatch.setattr(scraper_module, "fetch_page_impersonated", lambda url: None)
    monkeypatch.setattr(scraper_module, "fetch_page_api", lambda url: None)
    seen = {}

    def fake_browser(url, **kwargs):
        seen.update(kwargs)
        return "page"

    monkeypatch.setattr(scraper_module, "fetch_page_browser", fake_browser)

    fetch_page("https://example.com/wiki/X", challenge_timeout=120)

    assert seen["timeout_ms"] == 120_000


def test_build_parser_accepts_challenge_timeout() -> None:
    args = build_parser().parse_args(["--challenge-timeout", "90"])

    assert args.challenge_timeout == 90
