"""Write the API's OpenAPI document to apps/web/src/api/openapi.json.

The frontend generates its TypeScript types from this file (``pnpm --filter web gen:api``), so
frontend and backend types cannot drift silently. CI regenerates it and fails on any diff.

Usage: uv run python scripts/export_openapi.py [--check]
"""

import argparse
import json
import sys
from pathlib import Path

from weta_api.config import Settings
from weta_api.main import create_app

OUTPUT = Path(__file__).resolve().parents[1] / "apps" / "web" / "src" / "api" / "openapi.json"


def render() -> str:
    """The OpenAPI document as stable, sorted JSON text."""
    app = create_app(Settings(_env_file=None, environment="development"))  # type: ignore[call-arg]
    return json.dumps(app.openapi(), indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail if the file is out of date")
    args = parser.parse_args()
    text = render()
    if args.check:
        current = OUTPUT.read_text(encoding="utf-8") if OUTPUT.exists() else ""
        if current != text:
            print(f"{OUTPUT} is out of date; run scripts/export_openapi.py", file=sys.stderr)
            return 1
        return 0
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(text, encoding="utf-8", newline="\n")
    print(f"wrote {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
