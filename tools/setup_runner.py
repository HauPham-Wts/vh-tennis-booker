"""Set up the runner folder that the daily scheduled task runs from.

The scheduled task books for real, so it must never run work in progress. It runs a separate
git worktree checked out at a release tag, with its own virtual environment. Data stays in
the development folder: the task reads the same config.toml and writes the same logs.

Usage:
    python tools/setup_runner.py v0.4.0             # create the runner or move it to a tag
    python tools/setup_runner.py v0.4.0 --schedule  # also point the scheduled task at it
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DEFAULT_RUNNER = REPO.parent / "runner"
DEFAULT_CONFIG = REPO / "config.toml"


def venv_python(runner: Path) -> Path:
    """Return the interpreter of the runner's virtual environment."""
    return runner / ".venv" / "Scripts" / "python.exe"


def plan(
    *,
    repo: Path,
    runner: Path,
    tag: str,
    config: Path,
    schedule: bool,
    base_python: Path,
) -> list[list[str]]:
    """Return the commands that put ``runner`` at ``tag`` and install it there."""
    if runner.exists():
        commands = [["git", "-C", str(runner), "checkout", "--detach", tag]]
    else:
        commands = [["git", "-C", str(repo), "worktree", "add", "--detach", str(runner), tag]]
    python = venv_python(runner)
    if not python.exists():
        commands.append([str(base_python), "-m", "venv", str(runner / ".venv")])
    commands.append([str(python), "-m", "pip", "install", "--quiet", "-e", str(runner)])
    if schedule:
        commands.append(
            [str(python), "-m", "court_booker", "schedule", "install", "--config", str(config)]
        )
    return commands


def expected_version(tag: str) -> str:
    """Return the version string ``court-booker --version`` prints for ``tag``."""
    return f"court-booker {tag.removeprefix('v')}"


def git_output(*args: str) -> str:
    return subprocess.run(["git", *args], capture_output=True, text=True, check=False).stdout


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("tag", help="release tag to run, e.g. v0.4.0")
    parser.add_argument("--runner", type=Path, default=DEFAULT_RUNNER)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument(
        "--schedule", action="store_true", help="re-register the scheduled task on the runner"
    )
    args = parser.parse_args()

    tag_commit = f"{args.tag}^{{commit}}"
    if not git_output("-C", str(REPO), "rev-parse", "--verify", "--quiet", tag_commit):
        print(f"Unknown tag {args.tag!r}; fetch it first (git fetch --tags)")
        return 1
    if args.runner.exists() and git_output("-C", str(args.runner), "status", "--porcelain"):
        print(f"{args.runner} has local changes; the runner must stay a clean release")
        return 1
    if args.schedule and not args.config.is_file():
        print(f"{args.config} not found")
        return 1

    commands = plan(
        repo=REPO,
        runner=args.runner,
        tag=args.tag,
        config=args.config.resolve(),
        schedule=args.schedule,
        base_python=Path(sys.executable),
    )
    for command in commands:
        print("+", " ".join(command))
        subprocess.run(command, check=True)

    version = subprocess.run(
        [str(venv_python(args.runner)), "-m", "court_booker", "--version"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    if version != expected_version(args.tag):
        print(f"Runner reports {version!r}, expected {expected_version(args.tag)!r}")
        return 1
    print(f"Runner at {args.runner} runs {version}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
