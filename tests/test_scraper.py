from pathlib import Path

from nanoblock_scraper import parse_products


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
