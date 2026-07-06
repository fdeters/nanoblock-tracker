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
)


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    load_environment_config(args.env_file)

    sheet_id = resolve_config_value(args.sheet_id, "GOOGLE_SHEET_ID")
    credentials_path = resolve_config_value(
        args.credentials,
        "GOOGLE_APPLICATION_CREDENTIALS",
    )
    sheet_name = (
        resolve_config_value(args.sheet_name, "GOOGLE_SHEET_NAME", "Sheet1") or "Sheet1"
    )

    try:
        html = fetch_page(args.url)
    except Exception as exc:
        raise SystemExit(f"Scrape failed: {exc}") from exc

    products = parse_products(html)
    print(f"Scraped {len(products)} products from Bulbapedia.")

    if sheet_id:
        try:
            existing_rows = read_google_sheet_rows(
                sheet_id,
                sheet_name,
                credentials_path,
            )
            new_products = merge_products(products, existing_rows)
            appended = append_google_sheet_rows(
                sheet_id,
                new_products,
                sheet_name,
                credentials_path,
            )
        except (RuntimeError, FileNotFoundError) as exc:
            raise SystemExit(str(exc)) from exc

        if appended:
            print(f"Synced to Google Sheet '{sheet_name}' (sheet: {sheet_id}).")
            print(build_summary(new_products))
        else:
            print(f"No new products — '{sheet_name}' is already up to date.")
    else:
        export_products(products, args.output)
        print(f"Wrote {len(products)} products to {args.output}.")


if __name__ == "__main__":
    main()
