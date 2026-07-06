from scripts.run_monthly_sync import build_notification_body


def test_build_notification_body_formats_appended_products() -> None:
    products = [
        {
            "Product Code": "NBPM_001",
            "Product Name": "Pikachu",
            "Variant": "RS",
        },
        {
            "Product Code": "NBPM_002",
            "Product Name": "Eevee",
            "Variant": "",
        },
    ]

    body = build_notification_body(products)

    assert "Added 2 new Nanoblock product(s):" in body
    assert "NBPM_001: Pikachu (RS)" in body
    assert "NBPM_002: Eevee" in body
