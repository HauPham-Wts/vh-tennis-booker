"""Make the release commit of version X.Y.Z on its own chore/release-X.Y.Z branch.

Step 1 of CONTRIBUTING's "Releasing", run on a clean ``develop`` that matches GitHub's. It
sets ``__version__``, writes ui/openapi.json (the schema carries the version), moves the
"Unreleased" entries of CHANGELOG.md under a heading for the version, commits on the new
branch and prints the two pull requests to open. The tag workflow tags the merge on main.

Usage:
    python tools/release.py 0.19.0          # branch and commit
    python tools/release.py 0.19.0 --push   # also push the branch
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
INIT = REPO / "src" / "court_booker" / "__init__.py"
CHANGELOG = REPO / "CHANGELOG.md"
GITHUB = "https://github.com/servedbyhau/vh-tennis-booker"
UNRELEASED = "## [Unreleased]"
_VERSION_LINE = re.compile(r'^__version__ = "([^"]*)"$', re.MULTILINE)


def parse_version(text: str) -> tuple[int, int, int]:
    """Return ``X.Y.Z`` as three numbers; raise :class:`ValueError` for anything else."""
    found = re.fullmatch(r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)", text)
    if found is None:
        raise ValueError(f"{text!r} is not a version like 0.19.0")
    major, minor, patch = (int(part) for part in found.groups())
    return major, minor, patch


def current_version(init_text: str) -> str:
    """Return the version ``__init__.py`` sets."""
    found = _VERSION_LINE.findall(init_text)
    if len(found) != 1:
        raise ValueError("__init__.py must set __version__ once")
    return found[0]


def set_version(init_text: str, version: str) -> str:
    """Return ``__init__.py`` with ``__version__`` set to ``version``."""
    current_version(init_text)
    return _VERSION_LINE.sub(f'__version__ = "{version}"', init_text)


def release_changelog(text: str, version: str, day: date) -> str:
    """Return the changelog with the "Unreleased" entries under a heading for ``version``.

    "Unreleased" stays, empty, for the next changes. Raises :class:`ValueError` when it
    holds nothing: a release without changes is a mistake.
    """
    head, found, rest = text.partition(UNRELEASED + "\n")
    if not found:
        raise ValueError(f"CHANGELOG.md has no {UNRELEASED!r} line")
    end = rest.find("\n## [")
    entries, older = (rest, "") if end < 0 else (rest[:end], rest[end + 1 :])
    entries = entries.strip("\n")
    if not entries.strip():
        raise ValueError("CHANGELOG.md has nothing under Unreleased")
    if f"## [{version}]" in older:
        raise ValueError(f"CHANGELOG.md already has a section for {version}")
    released = f"{UNRELEASED}\n\n## [{version}] - {day.isoformat()}\n\n{entries}\n"
    return head + released + ("\n" + older if older else "")


def problems(
    version: str,
    current: str,
    *,
    branch: str,
    clean: bool,
    in_sync: bool,
    exists: bool,
) -> list[str]:
    """Return why ``version`` cannot be released from the repository's state; empty if it can.

    ``exists``: its branch or tag is there already.
    """
    try:
        new = parse_version(version)
    except ValueError as exc:
        return [str(exc)]
    found = []
    if new <= parse_version(current):
        found.append(f"{version} is not after the current version {current}")
    if branch != "develop":
        found.append(f"on {branch!r}: a release is cut from develop")
    if not clean:
        found.append("the working tree has changes: commit or stash them")
    if not in_sync:
        found.append("develop differs from origin/develop: pull or push first")
    if exists:
        found.append(f"chore/release-{version} or v{version} exists already")
    return found


def next_steps(version: str, pushed: bool) -> list[str]:
    """Return what is left after the release commit, with the pull requests to open."""
    branch = f"chore/release-{version}"
    steps = [] if pushed else [f"git push -u origin {branch}"]
    steps += [
        f"Pull request into develop, titled 'chore: release v{version}', merge commit: "
        f"{GITHUB}/compare/develop...{branch}",
        f"Then from develop into main, titled 'Release v{version}', merge commit: "
        f"{GITHUB}/compare/main...develop (the tag workflow tags it v{version})",
        f"Once a dry run passes: python tools/setup_runner.py v{version}",
    ]
    return steps


def git(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    """Run git in the repository and return the finished process."""
    return subprocess.run(
        ["git", "-C", str(REPO), *args], capture_output=True, text=True, check=check
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("version", help="the version to release, e.g. 0.19.0")
    parser.add_argument("--push", action="store_true", help="push the release branch")
    args = parser.parse_args()
    version: str = args.version
    branch = f"chore/release-{version}"

    if git("fetch", "--quiet", "origin", "develop", check=False).returncode != 0:
        print("Could not fetch origin/develop")
        return 1
    init_text = INIT.read_text(encoding="utf-8")
    exists = any(
        git("rev-parse", "--verify", "--quiet", ref, check=False).returncode == 0
        for ref in (f"refs/heads/{branch}", f"refs/tags/v{version}")
    ) or bool(git("ls-remote", "--heads", "--tags", "origin", branch, f"v{version}").stdout)
    found = problems(
        version,
        current_version(init_text),
        branch=git("rev-parse", "--abbrev-ref", "HEAD").stdout.strip(),
        clean=not git("status", "--porcelain").stdout,
        in_sync=git("rev-parse", "HEAD").stdout == git("rev-parse", "origin/develop").stdout,
        exists=exists,
    )
    # Both files are worked out before anything changes, so a refusal leaves no trace.
    try:
        changelog = release_changelog(CHANGELOG.read_text(encoding="utf-8"), version, date.today())
    except ValueError as exc:
        found.append(str(exc))
    if found:
        print("Not released:", *found, sep="\n- ")
        return 1

    git("switch", "--quiet", "-c", branch)
    INIT.write_text(set_version(init_text, version), encoding="utf-8", newline="\n")
    CHANGELOG.write_text(changelog, encoding="utf-8", newline="\n")
    # Only the schema's version changes, which the generated UI types do not hold.
    export = [sys.executable, str(REPO / "tools" / "export_openapi.py")]
    exported = subprocess.run(export, capture_output=True, text=True, check=False)
    if exported.returncode != 0:
        output = (exported.stdout + exported.stderr).strip()
        if output:
            print(output)
        print(
            "export_openapi.py failed (is the app extra installed?); to start again:",
            "git restore .",
            "git switch develop",
            f"git branch -D {branch}",
            sep="\n",
        )
        return 1
    git("add", "--", "CHANGELOG.md", "src/court_booker/__init__.py", "ui/openapi.json")
    git("commit", "--quiet", "-m", f"chore: release v{version}")
    print(f"Committed 'chore: release v{version}' on {branch}")
    left = git("status", "--porcelain").stdout
    if left:
        print("Not committed (develop was not in sync with the backend?):", left, sep="\n")
    if args.push:
        git("push", "--quiet", "-u", "origin", branch)
    print("Next:", *next_steps(version, args.push), sep="\n- ")
    return 0


if __name__ == "__main__":
    sys.exit(main())
