from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List


def build_notification_body(products: List[Dict[str, Any]]) -> str:
    if not products:
        return "No new Nanoblock products were added."

    lines = [f"Added {len(products)} new Nanoblock product(s):"]
    for product in products[:10]:
        code = product.get("Product Code", "")
        name = product.get("Product Name", "")
        variant = product.get("Variant", "")
        suffix = f" ({variant})" if variant else ""
        lines.append(f"- {code}: {name}{suffix}")
    if len(products) > 10:
        lines.append(f"...and {len(products) - 10} more")
    return "\n".join(lines)


def send_notification(summary_path: str, recipient: str | None = None) -> None:
    summary = Path(summary_path).read_text(encoding="utf-8")
    recipient = (recipient or os.environ.get("NOTIFICATION_EMAIL", "")).strip()
    if not recipient:
        print("No notification email configured; skipping mail send.")
        return

    subject = "Nanoblock tracker update: new records added"
    subprocess.run(["mail", "-s", subject, recipient], input=summary.encode("utf-8"), check=False)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("Usage: run_monthly_sync.py <summary-file> <recipient>")

    summary_path = sys.argv[1]
    recipient = sys.argv[2]
    send_notification(summary_path, recipient)
