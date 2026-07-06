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

## Test

```bash
python3 -m pytest -q
```
