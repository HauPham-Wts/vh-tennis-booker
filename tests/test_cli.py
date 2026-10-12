"""CLI exit codes with the device layer replaced by fakes."""

import argparse
import sys
from datetime import datetime
from pathlib import Path

import court_booker.cli as cli
from court_booker.errors import EmulatorError
from court_booker.runner import RoundResult


def fake_run(outcomes):
    def run_booking(device, config, *, results, **kwargs):
        run_booking.kwargs = kwargs
        for slot, ok in outcomes:
            if ok is KeyboardInterrupt:
                raise KeyboardInterrupt
            results.append(RoundResult(slot, ok, "detail", 1.0))
        return results

    return run_booking


def run_cli(monkeypatch, tmp_path, outcomes=(), connect=lambda config: object(), args=()):
    monkeypatch.setattr(cli, "connect_device", connect)
    monkeypatch.setattr(cli, "run_booking", fake_run(outcomes))
    return cli.main(["--config", str(tmp_path / "missing.toml"), *args])


def test_all_rounds_ok_exits_0(monkeypatch, tmp_path):
    assert run_cli(monkeypatch, tmp_path, [("18:00 - 19:00", True)]) == cli.EXIT_OK


def test_failed_round_exits_1(monkeypatch, tmp_path):
    outcomes = [("18:00 - 19:00", False), ("19:00 - 20:00", True)]
    assert run_cli(monkeypatch, tmp_path, outcomes) == cli.EXIT_ROUND_FAILED


def test_bad_config_exits_2(monkeypatch, tmp_path):
    path = tmp_path / "config.toml"
    path.write_text("unknown = 1\n", encoding="utf-8")
    monkeypatch.setattr(cli, "connect_device", lambda config: object())
    assert cli.main(["--config", str(path)]) == cli.EXIT_BAD_REQUEST


def test_device_error_exits_3(monkeypatch, tmp_path):
    def connect(config):
        raise EmulatorError("MuMu did not start")

    assert run_cli(monkeypatch, tmp_path, connect=connect) == cli.EXIT_DEVICE


def test_ctrl_c_prints_finished_rounds_and_exits_130(monkeypatch, tmp_path, capsys):
    outcomes = [("18:00 - 19:00", True), ("19:00 - 20:00", KeyboardInterrupt)]

    assert run_cli(monkeypatch, tmp_path, outcomes) == cli.EXIT_INTERRUPTED
    out = capsys.readouterr().out
    assert "Summary" in out
    assert "OK   18:00 - 19:00" in out


def test_passed_start_time_exits_2_before_connecting(monkeypatch, tmp_path):
    def connect(config):
        raise AssertionError("must not connect")

    monkeypatch.setattr(cli, "datetime", FixedDatetime)
    code = run_cli(monkeypatch, tmp_path, connect=connect, args=["--at", "05:00"])
    assert code == cli.EXIT_BAD_REQUEST


def test_scheduled_uses_config_start_and_clock_offset(monkeypatch, tmp_path):
    monkeypatch.setattr(cli, "datetime", FixedDatetime)
    monkeypatch.setattr(cli, "ntp_offset", lambda server: 0.25)
    run = fake_run([("18:00 - 19:00", True)])
    monkeypatch.setattr(cli, "connect_device", lambda config: object())
    monkeypatch.setattr(cli, "run_booking", run)

    assert cli.main(["--config", str(tmp_path / "missing.toml"), "--scheduled"]) == 0
    assert run.kwargs["start"] == datetime(2026, 10, 8, 6, 0)
    assert run.kwargs["offset"] == 0.25


class FixedDatetime(datetime):
    @classmethod
    def now(cls, tz=None):
        return datetime(2026, 10, 8, 5, 45)


def test_summary_is_sent_to_telegram_even_on_device_error(monkeypatch, tmp_path):
    path = tmp_path / "config.toml"
    path.write_text('telegram_token = "t"\ntelegram_chat_id = "42"\n', encoding="utf-8")
    sent = []
    monkeypatch.setattr(cli, "send_telegram", lambda token, chat, text: sent.append(text))

    def connect(config):
        raise EmulatorError("MuMu did not start")

    monkeypatch.setattr(cli, "connect_device", connect)
    assert cli.main(["--config", str(path)]) == cli.EXIT_DEVICE
    assert sent == ["court-booker: 0/0 ok\nError: MuMu did not start"]


def test_log_names_the_python_and_code_folder(monkeypatch, tmp_path):
    run_cli(monkeypatch, tmp_path, [("18:00 - 19:00", True)])

    text = next((tmp_path / "logs").glob("court-booker-*.log")).read_text(encoding="utf-8")
    assert f"Python {sys.executable}, code in " in text
    assert str(Path(cli.__file__).resolve().parent) in text


def read_log(tmp_path):
    return next((tmp_path / "logs").glob("court-booker-*.log")).read_text(encoding="utf-8")


def test_run_events_reach_the_log(monkeypatch, tmp_path):
    run_cli(monkeypatch, tmp_path, [("18:00 - 19:00", True)], args=["--dry-run"])

    text = read_log(tmp_path)
    assert "Event run_started trigger='dry_run' dry_run=True" in text
    assert "Event device_ready" in text
    assert "Event run_finished status='ok' booked=1 total=1 error=None" in text


def test_run_finished_is_reported_on_a_device_error(monkeypatch, tmp_path):
    def connect(config):
        raise EmulatorError("MuMu did not start")

    run_cli(monkeypatch, tmp_path, connect=connect)

    assert "Event run_finished status='failed' booked=0 total=0" in read_log(tmp_path)


def test_run_trigger():
    def args(scheduled=False, dry_run=False):
        return argparse.Namespace(scheduled=scheduled, dry_run=dry_run)

    assert cli.run_trigger(args(scheduled=True, dry_run=True)) == "scheduled"
    assert cli.run_trigger(args(dry_run=True)) == "dry_run"
    assert cli.run_trigger(args()) == "manual"


def test_run_status():
    ok = RoundResult("18:00 - 19:00", True, "booked", 7.0)
    failed = RoundResult("19:00 - 20:00", False, "Hết chỗ", 1.0)

    assert cli.run_status([ok, ok], None, interrupted=False) == "ok"
    assert cli.run_status([ok, failed], None, interrupted=False) == "partial"
    assert cli.run_status([ok], "adb lost", interrupted=False) == "partial"
    assert cli.run_status([failed], None, interrupted=False) == "failed"
    assert cli.run_status([], "MuMu did not start", interrupted=False) == "failed"
    assert cli.run_status([ok], "interrupted", interrupted=True) == "interrupted"
