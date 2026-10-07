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

This writes `output/nanoblock_products.csv` (the `output/` folder is git-ignored). Passing `--output name.csv` also writes to `output/` (use a path with a folder to write elsewhere) and skips the Google Sheets update.

## Sync to Google Sheets

To update an existing Google Sheet without overwriting prior tracking data, provide the spreadsheet ID and either a service-account JSON credentials file or the raw JSON contents of the credentials.

You can use either a `.env` file or inline arguments. Inline arguments take precedence.

Example `.env`:

```env
GOOGLE_SHEET_ID=your_spreadsheet_id
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
GOOGLE_WORKSHEET_NAME=pokemon
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
- fill missing release dates on existing rows
- append only new products
- leave existing rows and your manual tracking values untouched

## Run on Windows (scheduled task)

Bulbapedia is behind Cloudflare and blocks GitHub-hosted runners, so the recommended way to run the monthly sync is a Windows scheduled task on a home connection.

1. Install Python 3.11 (check "Add to PATH") and verify with `py -3.11 --version`.
2. Clone the repo to a stable path, e.g. `C:\Tools\nanoblock-tracker`.
3. Create the virtual environment and install dependencies:

   ```powershell
   cd C:\Tools\nanoblock-tracker
   py -3.11 -m venv .venv
   .venv\Scripts\pip install -r requirements.txt
   .venv\Scripts\python -m playwright install chromium
   ```

4. Create `.env` in the repo root with `GOOGLE_SHEET_ID`, `GOOGLE_APPLICATION_CREDENTIALS` (absolute path to the service-account JSON, kept outside the repo or in the git-ignored `credentials/` folder) and optionally `GOOGLE_WORKSHEET_NAME`. Share the sheet with the service account's email as an editor.
5. Verify the scrape works from your PC without updating the sheet: `.venv\Scripts\python nanoblock_scraper.py --sheet-id "" --output test.csv`. See [Blocked requests](#blocked-requests-cloudflare) if it fails.
6. Test the wrapper: `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run_sync.ps1`. It appends timestamped output to `logs\sync-YYYY-MM.log` and returns the scraper's exit code.
7. In Task Scheduler, create a task:
   - Trigger: Monthly, day 1, 9:00 AM.
   - Action: program `powershell.exe`, arguments `-NoProfile -ExecutionPolicy Bypass -File C:\Tools\nanoblock-tracker\scripts\run_sync.ps1`, "Start in" `C:\Tools\nanoblock-tracker`. The wrapper runs the scraper with `--challenge-timeout 120`, giving the browser fallback two minutes to clear a Cloudflare challenge; edit `run_sync.ps1` to change it.
   - Settings: run as soon as possible after a missed start, start only if a network connection is available, and retry on failure (e.g. every 30 minutes, up to 3 times).
8. Right-click the task and choose Run, then check the log and the sheet.

Each run of `run_sync.ps1` first runs `git pull --ff-only` and reinstalls dependencies only if `requirements.txt` changed since the last successful install (tracked in `.venv\requirements.sha256`). If either step fails, the failure is logged and the sync continues with the current checkout. Keep the clone free of local edits so the fast-forward pull succeeds.

## Blocked requests (Cloudflare)

Bulbapedia's Cloudflare returns 403 to plain `requests`. On a 403 the scraper tries these fallbacks in order and uses the first that works:

1. A Chrome-impersonating HTTP client (`curl_cffi`).
2. The MediaWiki API.
3. A visible Chrome/Chromium window (Playwright). It waits up to 20 seconds (override with `--challenge-timeout SECONDS`) for the page to load and uses a persistent `.browser-profile/` folder so Cloudflare clearance is reused between runs. If a checkbox challenge appears, click it in that window.
4. The latest Wayback Machine copy of the page, which may be slightly stale. It retries up to 3 times on HTTP 429/5xx (honouring `Retry-After`, otherwise waiting 5s then 15s) and logs the snapshot date.

## GitHub Actions sync (manual)

A GitHub Actions workflow is included at [.github/workflows/monthly-nanoblock-sync.yml](.github/workflows/monthly-nanoblock-sync.yml). Its monthly schedule is disabled because GitHub-hosted runners are blocked by Bulbapedia (HTTP 403); it can still be triggered manually.

### GitHub setup

In GitHub, add these repository secrets or variables:

- Secret: `GOOGLE_CREDENTIALS_JSON`
  - The full JSON contents of your Google service-account credentials file.
- Secret: `GOOGLE_SHEET_ID`
  - The Google Sheets spreadsheet ID.
- Variable (optional): `GOOGLE_WORKSHEET_NAME`
  - The worksheet/tab name to update. If omitted, the script falls back to `pokemon`.

The workflow publishes the scraper output to the GitHub Actions job summary (`$GITHUB_STEP_SUMMARY`) so each run includes a built-in sync status message in the Actions UI.

### How to include the Google credentials in GitHub

1. Create or download a Google service-account JSON key from Google Cloud.
2. In your GitHub repository, open Settings → Secrets and variables → Actions.
3. Add a new repository secret named `GOOGLE_CREDENTIALS_JSON` and paste the entire JSON contents as the value.
4. Add another secret named `GOOGLE_SHEET_ID` with the spreadsheet ID.
5. Optional: add a repository variable named `GOOGLE_WORKSHEET_NAME` if your worksheet (tab) is not named `pokemon`.

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
