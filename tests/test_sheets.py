from nanoblock_tracker.sheets import normalize_sheet_row


def test_normalize_sheet_row_uses_expected_fields() -> None:
    row = {"Product Name": "Pikachu", "Product Code": "NBPM_001"}

    normalized = normalize_sheet_row(row)

    assert normalized["Product Name"] == "Pikachu"
    assert normalized["Product Code"] == "NBPM_001"
    assert normalized["Variant"] == ""
    assert normalized["Collected"] == ""
    assert normalized["Not interested"] == ""


def test_normalize_sheet_row_fills_missing_fields_with_empty_strings() -> None:
    normalized = normalize_sheet_row({})

    assert normalized == {
        "Product Name": "",
        "Product Code": "",
        "Variant": "",
        "Collected": "",
        "Not interested": "",
    }
