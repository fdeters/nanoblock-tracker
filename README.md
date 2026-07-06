# Nanoblock Tracker

This project scrapes the Bulbapedia Nanoblock products page and exports a spreadsheet-friendly CSV of valid Nanoblock products.

## Requirements

- Python 3.11+

## Setup

Create and activate a project-local virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt -r requirements-dev.txt
```

## Run

```bash
python nanoblock_scraper.py
```

This writes a file named `nanoblock_products.csv` in the project root.

## Sync to Google Sheets

To update an existing Google Sheet without overwriting prior tracking data, provide the spreadsheet ID and either a service-account JSON credentials file or the raw JSON contents of the credentials.

You can use either a `.env` file or inline arguments. Inline arguments take precedence.

Example `.env`:

```env
GOOGLE_SHEET_ID=your_spreadsheet_id
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
GOOGLE_SHEET_NAME=Sheet1
```

Then run:

```bash
python nanoblock_scraper.py
```

Or override them explicitly:

```bash
python nanoblock_scraper.py \
  --sheet-id YOUR_SPREADSHEET_ID \
  --credentials /path/to/service-account.json
```

Or pass the credentials inline as a JSON string:

```bash
python nanoblock_scraper.py \
  --sheet-id YOUR_SPREADSHEET_ID \
  --credentials '{"type":"service_account",...}'
```

The script will:

- read the existing sheet rows
- compare them by `Product Code`
- append only new products
- leave existing rows and your manual tracking values untouched

## GitHub Actions monthly sync

A GitHub Actions workflow is included at [.github/workflows/monthly-nanoblock-sync.yml](.github/workflows/monthly-nanoblock-sync.yml). It runs on the first day of every month and can also be triggered manually.

### GitHub setup

In GitHub, add these repository secrets or variables:

- Secret: `GOOGLE_CREDENTIALS_JSON`
  - The full JSON contents of your Google service-account credentials file.
- Secret: `GOOGLE_SHEET_ID`
  - The Google Sheets spreadsheet ID.
- Variable (optional): `GOOGLE_SHEET_NAME`
  - The worksheet/tab name to update. If omitted, the script falls back to `Sheet1`.

The workflow publishes the scraper output to the GitHub Actions job summary (`$GITHUB_STEP_SUMMARY`) so each run includes a built-in sync status message in the Actions UI.

### How to include the Google credentials in GitHub

1. Create or download a Google service-account JSON key from Google Cloud.
2. In your GitHub repository, open Settings → Secrets and variables → Actions.
3. Add a new repository secret named `GOOGLE_CREDENTIALS_JSON` and paste the entire JSON contents as the value.
4. Add another secret named `GOOGLE_SHEET_ID` with the spreadsheet ID.
5. Optional: add a repository variable named `GOOGLE_SHEET_NAME` if your sheet is not named `Sheet1`.

> Keep the credentials JSON in GitHub Secrets, not in the repository itself. The workflow writes it to a temporary file at runtime and uses it for the sync. The same JSON payload can also be supplied directly when running locally with `--credentials`.

## Development

A small task runner is included so common developer commands are grouped like package.json scripts:

```bash
python tasks.py format
python tasks.py lint
python tasks.py typecheck
python tasks.py test
```

You can also run the underlying tools directly:

```bash
python -m black .
python -m ruff check .
python -m pyright
python -m pytest -q
```
