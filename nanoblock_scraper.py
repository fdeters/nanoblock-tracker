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

    html = fetch_page(args.url)
    products = parse_products(html)

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
            raise SystemExit(f"Google Sheets sync failed: {exc}") from exc

        if appended:
            print(f"Appended {appended} new products to Google Sheet {sheet_id}")
            print(build_summary(new_products))
        else:
            print("No new products to append to Google Sheet")
    else:
        export_products(products, args.output)
        print(f"Wrote {len(products)} products to {args.output}")


if __name__ == "__main__":
    main()
