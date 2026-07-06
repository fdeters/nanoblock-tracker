from pathlib import Path

from nanoblock_scraper import build_parser, merge_products, parse_products


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


def test_build_parser_leaves_sheet_name_unset_until_explicitly_provided(monkeypatch) -> None:
    monkeypatch.setenv("GOOGLE_SHEET_NAME", "Env Sheet")

    parser = build_parser()
    args = parser.parse_args([])

    assert args.sheet_name is None


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
