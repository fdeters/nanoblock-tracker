# Nanoblock Tracker

This project scrapes the Bulbapedia Nanoblock products page and exports a spreadsheet-friendly CSV of valid Nanoblock products.

## Setup

```bash
python3 -m pip install -r requirements.txt pytest
```

## Run

```bash
python3 nanoblock_scraper.py
```

This writes a file named `nanoblock_products.csv` in the project root.

## Sync to Google Sheets

To update an existing Google Sheet without overwriting prior tracking data, provide the spreadsheet ID and a service-account JSON credentials file.

You can use either a `.env` file or inline arguments. Inline arguments take precedence.

Example `.env`:

```env
GOOGLE_SHEET_ID=your_spreadsheet_id
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
GOOGLE_SHEET_NAME=Sheet1
```

Then run:

```bash
python3 nanoblock_scraper.py
```

Or override them explicitly:

```bash
python3 nanoblock_scraper.py \
  --sheet-id YOUR_SPREADSHEET_ID \
  --credentials /path/to/service-account.json
```

The script will:

- read the existing sheet rows
- compare them by `Product Code`
- append only new products
- leave existing rows and your manual tracking values untouched

## Test

```bash
python3 -m pytest -q
```
