from __future__ import annotations

import re

DEFAULT_URL = "https://bulbapedia.bulbagarden.net/wiki/" "Pok%C3%A9mon_Nanoblocks"
FIELDNAMES = [
    "Product Name",
    "Product Code",
    "Variant",
    "Collected",
    "Not interested",
]
PRODUCT_CODE_RE = re.compile(
    r"\bNBPM(?:_[0-9]{3}|_R[0-9]{2}|_XXX)\b",
    re.IGNORECASE,
)
VARIANT_RE = re.compile(
    r"\b(RS|DX|Extreme DX|Monotone|Translucent|Pokémon Quest|"
    r"Galarian Form|Brilliant Shining|Lunar New Year Costume)\b",
    re.IGNORECASE,
)
PARENTHETICAL_RE = re.compile(r"\s*\([^)]*\)\s*$")
