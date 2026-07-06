# Nanoblock Tracker Spec

This is a specification for a system that converts the contents of a web page listing Nanoblock products into a structured format (spreadsheet) where I can track which I have collected and which I still need to acquire.

## Data Source

I've been using this Bulbapedia page to track my Nanoblock Pokemon collection: https://bulbapedia.bulbagarden.net/wiki/Pok%C3%A9mon_Nanoblocks

## Requirements

- The system should be able to scrape the Nanoblock product listings from the provided Bulbapedia page.
- The system should extract relevant information for each Nanoblock product, including:
  - Product Name
  - Product Code
  - Variant/line type (e.g. RS, DX, 20th anniversary)
- Do not include Nanoblock+ sets or sets without a product code in the output.
- Output should be compatible with Google Sheets (spreadsheet will live in Google Sheets to be shareable).
- The process should be repeatable in the future to update the spreadsheet with new products.
