"""The UI's copy of the OpenAPI schema must match the backend."""

import sys
from pathlib import Path

import pytest

from court_booker.api.schema import openapi_json

SNAPSHOT = Path(__file__).resolve().parents[2] / "ui" / "openapi.json"


@pytest.mark.skipif(
    sys.version_info < (3, 10),
    reason="Python 3.9 gets older FastAPI and Pydantic releases, which word the schema differently",
)
def test_the_ui_schema_matches_the_backend():
    assert SNAPSHOT.read_text(encoding="utf-8") == openapi_json(), (
        "ui/openapi.json is out of date: run `python tools/export_openapi.py`, "
        "then `npm run api:types` in ui/"
    )


def test_the_schema_is_json_text_ending_with_a_newline():
    text = openapi_json()

    assert text.startswith('{\n  "openapi": ')
    assert text.endswith("}\n")
