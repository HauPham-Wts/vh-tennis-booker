"""Write the backend's OpenAPI schema to ui/openapi.json, where the UI's types come from.

Run it after changing a route or a model, then regenerate the types in ui/:
    python tools/export_openapi.py
    npm run api:types        (in ui/)

The backend tests fail while ui/openapi.json differs from the backend.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SNAPSHOT = REPO / "ui" / "openapi.json"


def main() -> int:
    """Write the schema and say whether it changed."""
    sys.path.insert(0, str(REPO / "src"))
    from court_booker.api.schema import openapi_json

    text = openapi_json()
    old = SNAPSHOT.read_text(encoding="utf-8") if SNAPSHOT.exists() else None
    if text == old:
        print(f"{SNAPSHOT.relative_to(REPO).as_posix()} is up to date")
        return 0
    SNAPSHOT.write_text(text, encoding="utf-8", newline="\n")
    print(f"Wrote {SNAPSHOT.relative_to(REPO).as_posix()}; now run `npm run api:types` in ui/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
