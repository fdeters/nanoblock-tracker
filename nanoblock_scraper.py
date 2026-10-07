from __future__ import annotations

from nanoblock_tracker import (
    append_google_sheet_rows,
    build_parser,
    build_summary,
    export_products,
    fetch_page,
    load_environment_config,
    merge_products,
    parse_products,
    read_google_sheet_rows,
    resolve_config_value,
    update_google_sheet_missing_data,
)
from nanoblock_tracker.constants import DEFAULT_WORKSHEET_NAME


def export_and_report(products: list[dict], output: str | None) -> None:
    path = export_products(products, output)
    print(f"Wrote {len(products)} products to {path}.")


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    load_environment_config(args.env_file)

    sheet_id = resolve_config_value(args.sheet_id, "GOOGLE_SHEET_ID")
    credentials_path = resolve_config_value(
        args.credentials,
        "GOOGLE_APPLICATION_CREDENTIALS",
    )
    worksheet_name = (
        resolve_config_value(
            args.worksheet_name,
            "GOOGLE_WORKSHEET_NAME",
            DEFAULT_WORKSHEET_NAME,
        )
        or DEFAULT_WORKSHEET_NAME
    )

    try:
        html = fetch_page(args.url, args.challenge_timeout)
    except Exception as exc:
        raise SystemExit(f"Scrape failed: {exc}") from exc

    products = parse_products(html)
    print(f"Scraped {len(products)} products from Bulbapedia.")

    if args.output:
        if sheet_id:
            print("--output was given; skipping the Google Sheets update.")
        export_and_report(products, args.output)
    elif sheet_id:
        try:
            existing_rows = read_google_sheet_rows(
                sheet_id,
                worksheet_name,
                credentials_path,
            )
            updated_cells = update_google_sheet_missing_data(
                sheet_id,
                products,
                existing_rows,
                worksheet_name,
                credentials_path,
            )
            new_products = merge_products(products, existing_rows)
            appended = append_google_sheet_rows(
                sheet_id,
                new_products,
                worksheet_name,
                credentials_path,
            )
        except (RuntimeError, FileNotFoundError) as exc:
            raise SystemExit(str(exc)) from exc

        if appended or updated_cells:
            print(f"Synced to worksheet '{worksheet_name}' of Google Sheet {sheet_id}.")
            if appended:
                print(build_summary(new_products))
            if updated_cells:
                print(f"Filled {updated_cells} missing value(s) for existing products.")
        else:
            print(
                f"No new products — worksheet '{worksheet_name}' is already up to date."
            )
    else:
        export_and_report(products, None)


if __name__ == "__main__":
    main()
