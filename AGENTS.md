# AGENTS.md

## Project overview

This repository contains a Python-based Nanoblock tracker that scrapes product listings from Bulbapedia, normalizes the data, and can export it to CSV or sync new items to Google Sheets. Google Sheets authentication can be provided either as a credentials file path or as an inline JSON string.

## Repository structure

- `nanoblock_scraper.py`: CLI entrypoint for running the tracker.
- `nanoblock_tracker/`: Main package containing the modular implementation.
  - `config.py`: CLI and environment configuration handling.
  - `scraper.py`: Scraping, parsing, normalization, merge logic, CSV export, and summary generation.
  - `sheets.py`: Google Sheets read/write helpers.
  - `constants.py`: Shared constants and regex patterns.
- `scripts/`: Helper scripts for automation workflows.
- `tests/`: Unit tests for the scraper and supporting modules.
- `tasks.py`: Lightweight task runner for common developer commands.

## Development workflow

- Use Python 3.11.
- Install dependencies from `requirements.txt` and `requirements-dev.txt`.
- Common checks are available through `python tasks.py ci`.
- Prefer keeping behavior stable when refactoring; update tests when public behavior changes.

## Conventions

- Follow existing Python style and keep functions focused on a single responsibility.
- Preserve the current CLI behavior unless the task explicitly changes it.
- When changing scraping, config, or sync behavior, add or update tests to cover the change.
