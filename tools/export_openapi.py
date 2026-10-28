"""Write what the UI takes from the backend: ui/openapi.json and ui/src/catalog.json.

The OpenAPI schema is where the UI's types come from; the catalog holds the subdivisions,
sports and courts the settings offer (court_booker.catalog). Run it after changing a
route, a model or the catalog, then regenerate the types in ui/:
    python tools/export_openapi.py
    npm run api:types        (in ui/)

The backend tests fail while either file differs from the backend.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SNAPSHOT = REPO / "ui" / "openapi.json"
CATALOG = REPO / "ui" / "src" / "catalog.json"


def write(path: Path, text: str) -> bool:
    """Write ``text`` to ``path`` unless it holds it already; return whether it changed."""
    name = path.relative_to(REPO).as_posix()
    if path.exists() and path.read_text(encoding="utf-8") == text:
        print(f"{name} is up to date")
        return False
    path.write_text(text, encoding="utf-8", newline="\n")
    print(f"Wrote {name}")
    return True


def main() -> int:
    """Write both files and say what changed."""
    sys.path.insert(0, str(REPO / "src"))
    from court_booker.api.schema import openapi_json
    from court_booker.catalog import catalog_json

    if write(SNAPSHOT, openapi_json()):
        print("Now run `npm run api:types` in ui/")
    write(CATALOG, catalog_json())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
