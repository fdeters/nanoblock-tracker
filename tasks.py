import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def run(command: list[str]) -> None:
    subprocess.run(command, cwd=ROOT, check=True)


def format_code() -> None:
    run([sys.executable, "-m", "black", "."])


def lint_code() -> None:
    run([sys.executable, "-m", "ruff", "check", "."])


def type_check() -> None:
    run([sys.executable, "-m", "pyright"])


def test_code() -> None:
    run([sys.executable, "-m", "pytest", "-q"])


def ci() -> None:
    format_code()
    lint_code()
    type_check()
    test_code()


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("Usage: python tasks.py <format|lint|typecheck|test|ci>")

    action = sys.argv[1]
    if action == "format":
        format_code()
    elif action == "lint":
        lint_code()
    elif action == "typecheck":
        type_check()
    elif action == "test":
        test_code()
    elif action == "ci":
        ci()
    else:
        raise SystemExit(f"Unknown action: {action}")


if __name__ == "__main__":
    main()
