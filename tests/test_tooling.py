"""The Ruff version: pinned once in pyproject.toml, the same in pre-commit and CI."""

import re
import sys
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

REPO = Path(__file__).resolve().parents[1]


def pinned_ruff() -> str:
    """Return the Ruff version the dev extra pins in pyproject.toml."""
    data = tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))
    pins = [pin for pin in data["project"]["optional-dependencies"]["dev"] if "ruff" in pin]
    assert len(pins) == 1 and pins[0].startswith("ruff=="), pins
    return pins[0].removeprefix("ruff==")


def test_pre_commit_runs_the_pinned_ruff():
    text = (REPO / ".pre-commit-config.yaml").read_text(encoding="utf-8")
    found = re.search(r"astral-sh/ruff-pre-commit\s+rev:\s*v?(\S+)", text)

    assert found is not None
    # Dependabot bumps pyproject.toml only: set the hook's rev to the same version.
    assert found.group(1) == pinned_ruff()


def test_ci_installs_ruff_from_pyproject():
    text = (REPO / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

    # CI reads the pin from pyproject.toml; a version of its own would drift from it.
    assert "grep -o 'ruff==[0-9.]*' pyproject.toml" in text
    assert re.search(r"ruff==\d", text) is None
