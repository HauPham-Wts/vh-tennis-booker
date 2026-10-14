"""The backend's OpenAPI schema, as the UI's TypeScript types are generated from it."""

from __future__ import annotations

import json
from pathlib import Path

from court_booker.api.app import create_app
from court_booker.api.context import AppContext
from court_booker.paths import DataFolder


def openapi_json() -> str:
    """Return the OpenAPI schema as JSON text: two-space indent, routes in declared order."""
    # Building the schema opens no file, so placeholder paths serve.
    app = create_app(AppContext(Path("config.toml"), DataFolder(Path("."))))
    return json.dumps(app.openapi(), indent=2, ensure_ascii=False) + "\n"
