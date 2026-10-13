"""Tests for the runner folder tool; no git, pip or Task Scheduler calls."""

import importlib.util
from pathlib import Path

TOOL = Path(__file__).resolve().parents[1] / "tools" / "setup_runner.py"
_spec = importlib.util.spec_from_file_location("setup_runner", TOOL)
setup_runner = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(setup_runner)


def make_plan(tmp_path, schedule=False):
    return setup_runner.plan(
        repo=tmp_path / "repo",
        runner=tmp_path / "runner",
        tag="v0.4.0",
        config=tmp_path / "repo" / "config.toml",
        schedule=schedule,
        base_python=Path("python.exe"),
    )


def test_first_run_adds_a_worktree_and_a_venv(tmp_path):
    commands = make_plan(tmp_path)

    runner = str(tmp_path / "runner")
    assert commands[0] == [
        "git", "-C", str(tmp_path / "repo"), "worktree", "add", "--detach", runner, "v0.4.0"
    ]  # fmt: skip
    assert commands[1] == ["python.exe", "-m", "venv", str(tmp_path / "runner" / ".venv")]
    assert commands[2][-3:] == ["--quiet", "-e", runner]
    assert len(commands) == 3


def test_existing_runner_moves_to_the_tag_and_keeps_its_venv(tmp_path):
    python = setup_runner.venv_python(tmp_path / "runner")
    python.parent.mkdir(parents=True)
    python.touch()

    commands = make_plan(tmp_path)

    assert commands[0] == ["git", "-C", str(tmp_path / "runner"), "checkout", "--detach", "v0.4.0"]
    assert [command[0] for command in commands[1:]] == [str(python)]


def test_schedule_registers_the_task_with_the_runner_python(tmp_path):
    commands = make_plan(tmp_path, schedule=True)

    assert commands[-1] == [
        str(setup_runner.venv_python(tmp_path / "runner")),
        "-m", "court_booker", "schedule", "install",
        "--config", str(tmp_path / "repo" / "config.toml"),
    ]  # fmt: skip


def test_expected_version_drops_the_tag_prefix():
    assert setup_runner.expected_version("v0.4.0") == "court-booker 0.4.0"
