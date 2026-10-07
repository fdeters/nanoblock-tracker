import json

import pytest

import nanoblock_tracker.sheets as sheets_module
from nanoblock_tracker.sheets import (
    append_google_sheet_rows,
    normalize_sheet_row,
    update_google_sheet_missing_data,
)


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
        "Release Date": "",
        "Collected": "",
        "Not interested": "",
    }


def test_build_credentials_from_json_string(monkeypatch) -> None:
    payload = {
        "type": "service_account",
        "project_id": "demo-project",
        "private_key": "-----BEGIN PRIVATE KEY-----\nabc\n-----END PRIVATE KEY-----\n",
        "client_email": "demo@example.com",
        "token_uri": "https://oauth2.googleapis.com/token",
    }

    class DummyCredentials:
        @classmethod
        def from_service_account_info(cls, info, scopes=None):
            return {"info": info, "scopes": scopes}

    monkeypatch.setattr(sheets_module, "Credentials", DummyCredentials)

    credentials = sheets_module.build_credentials(json.dumps(payload))

    assert credentials == {
        "info": payload,
        "scopes": ["https://www.googleapis.com/auth/spreadsheets"],
    }


def test_read_google_sheet_rows_surfaces_missing_worksheet_error(monkeypatch) -> None:
    class DummyClient:
        def open_by_key(self, _spreadsheet_id):
            return type(
                "Workbook",
                (),
                {
                    "worksheet": lambda self, _worksheet_name: (_ for _ in ()).throw(
                        RuntimeError("Worksheet 'pokemon' not found")
                    )
                },
            )()

    class DummyGspread:
        @staticmethod
        def authorize(_credentials):
            return DummyClient()

    class DummyCredentials:
        @classmethod
        def from_service_account_info(cls, info, scopes=None):
            return {"info": info, "scopes": scopes}

    monkeypatch.setattr(sheets_module, "gspread", DummyGspread)
    monkeypatch.setattr(sheets_module, "Credentials", DummyCredentials)

    with pytest.raises(RuntimeError, match="Google Sheets sync failed") as exc_info:
        sheets_module.read_google_sheet_rows("sheet-id", "pokemon", "{}")

    assert "Worksheet 'pokemon' not found" in str(exc_info.value)


def test_append_google_sheet_rows_uses_sheet_header_order(monkeypatch) -> None:
    appended = []

    class DummyWorksheet:
        @staticmethod
        def row_values(_row):
            return ["Product Code", "Release Date", "Product Name", "Collected"]

        @staticmethod
        def append_rows(rows, value_input_option):
            appended.append((rows, value_input_option))

    class DummyClient:
        @staticmethod
        def open_by_key(_spreadsheet_id):
            return type(
                "Workbook",
                (),
                {"worksheet": lambda self, _worksheet_name: DummyWorksheet()},
            )()

    class DummyGspread:
        @staticmethod
        def authorize(_credentials):
            return DummyClient()

    class DummyCredentials:
        @classmethod
        def from_service_account_info(cls, info, scopes=None):
            return {"info": info, "scopes": scopes}

    monkeypatch.setattr(sheets_module, "gspread", DummyGspread)
    monkeypatch.setattr(sheets_module, "Credentials", DummyCredentials)

    count = append_google_sheet_rows(
        "sheet-id",
        [
            {
                "Product Code": "NBPM_001",
                "Release Date": "2015-03-01",
                "Product Name": "Pikachu",
                "Collected": "",
            }
        ],
        credentials_path="{}",
    )

    assert count == 1
    assert appended == [([["NBPM_001", "2015-03-01", "Pikachu", ""]], "USER_ENTERED")]


def test_update_google_sheet_missing_data_fills_any_blank_source_fields(
    monkeypatch,
) -> None:
    updates = []

    class DummyWorksheet:
        @staticmethod
        def row_values(_row):
            return ["Product Name", "Product Code", "Variant", "Release Date"]

        @staticmethod
        def batch_update(data, value_input_option):
            updates.append((data, value_input_option))

    class DummyClient:
        @staticmethod
        def open_by_key(_spreadsheet_id):
            return type(
                "Workbook",
                (),
                {"worksheet": lambda self, _worksheet_name: DummyWorksheet()},
            )()

    class DummyGspread:
        @staticmethod
        def authorize(_credentials):
            return DummyClient()

    class DummyCredentials:
        @classmethod
        def from_service_account_info(cls, info, scopes=None):
            return {"info": info, "scopes": scopes}

    monkeypatch.setattr(sheets_module, "gspread", DummyGspread)
    monkeypatch.setattr(sheets_module, "Credentials", DummyCredentials)

    count = update_google_sheet_missing_data(
        "sheet-id",
        [
            {
                "Product Code": "NBPM_001",
                "Product Name": "Pikachu",
                "Variant": "RS",
                "Release Date": "2015-03-01",
            },
            {
                "Product Code": "NBPM_002",
                "Product Name": "Eevee",
                "Release Date": "2016-08-12",
            },
            {"Product Code": "NBPM_003", "Release Date": ""},
        ],
        [
            {
                "Product Code": "NBPM_001",
                "Product Name": "",
                "Variant": "DX",
                "Release Date": "",
            },
            {
                "Product Code": "NBPM_002",
                "Product Name": "Eevee",
                "Release Date": "2016-01-01",
            },
        ],
        credentials_path="{}",
    )

    assert count == 2
    assert updates == [
        (
            [
                {"range": "A2", "values": [["Pikachu"]]},
                {"range": "D2", "values": [["2015-03-01"]]},
            ],
            "USER_ENTERED",
        )
    ]
