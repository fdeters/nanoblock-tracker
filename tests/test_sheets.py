import json

import pytest

import nanoblock_tracker.sheets as sheets_module
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
                    "worksheet": lambda self, _sheet_name: (_ for _ in ()).throw(
                        RuntimeError("Worksheet 'Sheet1' not found")
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
        sheets_module.read_google_sheet_rows("sheet-id", "Sheet1", "{}")

    assert "Worksheet 'Sheet1' not found" in str(exc_info.value)
