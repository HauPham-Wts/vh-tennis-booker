"""Tests for the release tool's file changes and checks; no git or export runs."""

import importlib.util
from datetime import date
from pathlib import Path

import pytest

TOOL = Path(__file__).resolve().parents[1] / "tools" / "release.py"
_spec = importlib.util.spec_from_file_location("release", TOOL)
release = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(release)

DAY = date(2026, 11, 2)
CHANGELOG = """# Changelog

Intro.

## [Unreleased]

### Changed
- Something new.

### Fixed
- Something broken.

## [0.18.1] - 2026-10-30

### Fixed
- An older fix.
"""


def ready(**changes):
    state = {"branch": "develop", "clean": True, "in_sync": True, "exists": False}
    return release.problems(changes.pop("version", "0.19.0"), "0.18.1", **{**state, **changes})


RELEASED = """# Changelog

Intro.

## [Unreleased]

## [0.19.0] - 2026-11-02

### Changed
- Something new.

### Fixed
- Something broken.

## [0.18.1] - 2026-10-30

### Fixed
- An older fix.
"""


def test_the_unreleased_entries_move_under_the_version():
    assert release.release_changelog(CHANGELOG, "0.19.0", DAY) == RELEASED


def test_a_first_release_has_no_older_section():
    text = "# Changelog\n\n## [Unreleased]\n\n### Added\n- All.\n"

    assert release.release_changelog(text, "0.1.0", DAY) == (
        "# Changelog\n\n## [Unreleased]\n\n## [0.1.0] - 2026-11-02\n\n### Added\n- All.\n"
    )


def test_an_empty_unreleased_section_is_refused():
    text = CHANGELOG.replace(
        "### Changed\n- Something new.\n\n### Fixed\n- Something broken.\n\n", ""
    )

    with pytest.raises(ValueError, match="nothing under Unreleased"):
        release.release_changelog(text, "0.19.0", DAY)


def test_a_version_released_already_is_refused():
    with pytest.raises(ValueError, match="already has a section"):
        release.release_changelog(CHANGELOG, "0.18.1", DAY)


def test_the_version_line_is_set():
    text = '"""Docstring."""\n\n__version__ = "0.18.1"\n'

    assert release.current_version(text) == "0.18.1"
    assert release.set_version(text, "0.19.0") == '"""Docstring."""\n\n__version__ = "0.19.0"\n'


def test_the_repository_version_line_is_found():
    assert release.parse_version(release.current_version(release.INIT.read_text("utf-8")))


@pytest.mark.parametrize("text", ["v0.19.0", "0.19", "0.19.0-rc1", "01.2.3", ""])
def test_only_plain_versions_parse(text):
    with pytest.raises(ValueError):
        release.parse_version(text)


def test_a_clean_develop_in_sync_can_release():
    assert ready() == []


def test_versions_compare_as_numbers():
    state = {"branch": "develop", "clean": True, "in_sync": True, "exists": False}

    assert release.problems("0.18.10", "0.18.9", **state) == []
    assert release.problems("0.9.0", "0.18.9", **state) != []


@pytest.mark.parametrize(
    ("changes", "reason"),
    [
        ({"version": "0.18.1"}, "not after the current version"),
        ({"version": "0.18.0"}, "not after the current version"),
        ({"version": "v0.19.0"}, "not a version"),
        ({"branch": "feat/x"}, "cut from develop"),
        ({"clean": False}, "working tree has changes"),
        ({"in_sync": False}, "differs from origin/develop"),
        ({"exists": True}, "exists already"),
    ],
)
def test_each_problem_is_named(changes, reason):
    found = ready(**changes)

    assert len(found) == 1
    assert reason in found[0]


def test_next_steps_name_both_pull_requests():
    steps = release.next_steps("0.19.0", pushed=False)

    assert steps[0] == "git push -u origin chore/release-0.19.0"
    assert steps[1].endswith("/compare/develop...chore/release-0.19.0")
    assert "/compare/main...develop" in steps[2]
    assert release.next_steps("0.19.0", pushed=True)[0] == steps[1]
