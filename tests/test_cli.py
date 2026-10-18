"""CLI exit codes with the device layer replaced by fakes."""

import argparse
import json
import logging
import os
import sqlite3
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pytest

import court_booker.cli as cli
from court_booker import device_setup, processes
from court_booker.cli import close_emulator
from court_booker.config import Config
from court_booker.device_setup import Check, Status
from court_booker.errors import AppNotReadyError, DeviceNotRespondingError, EmulatorError
from court_booker.history import HistoryHandler
from court_booker.lock import Holder
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


class FakeDevice:
    """A device driven the way ``driver`` asks; ``closed`` counts ``close()`` calls."""

    def __init__(self, driver, error=None):
        self.driver = driver
        self.error = error
        self.closed = 0

    def close(self):
        self.closed += 1
        if self.error is not None:
            raise self.error


def fake_connect(config, driver="auto"):
    """Stand in for ``connect_device``."""
    return FakeDevice("instrumentation" if driver == "auto" else driver)


def run_cli(monkeypatch, tmp_path, outcomes=(), connect=fake_connect, args=(), now=None):
    """Run the CLI with a fake device; the time is 05:40 unless ``now`` gives a class."""
    monkeypatch.setattr(cli, "connect_device", connect)
    monkeypatch.setattr(cli, "run_booking", fake_run(outcomes))
    monkeypatch.setattr(cli, "datetime", now or FixedDatetime)
    return cli.main(["--config", str(tmp_path / "missing.toml"), *args])


def test_all_rounds_ok_exits_0(monkeypatch, tmp_path):
    assert run_cli(monkeypatch, tmp_path, [("18:00 - 19:00", True)]) == cli.EXIT_OK


def test_failed_round_exits_1(monkeypatch, tmp_path):
    outcomes = [("18:00 - 19:00", False), ("19:00 - 20:00", True)]
    assert run_cli(monkeypatch, tmp_path, outcomes) == cli.EXIT_ROUND_FAILED


def test_the_driver_flag_reaches_the_device_and_the_history(monkeypatch, tmp_path):
    asked = []

    def connect(config, driver):
        asked.append(driver)
        return fake_connect(config, driver)

    events = []
    monkeypatch.setattr(
        cli, "Reporter", lambda sink: lambda kind, **data: events.append((kind, data))
    )
    run_cli(monkeypatch, tmp_path, [("18:00 - 19:00", True)], connect, ["--driver", "uiautomator2"])

    assert asked == ["uiautomator2"]
    assert ("device_ready", {"driver": "uiautomator2"}) in [(k.value, d) for k, d in events]


def test_bad_config_exits_2(monkeypatch, tmp_path):
    path = tmp_path / "config.toml"
    path.write_text("unknown = 1\n", encoding="utf-8")
    monkeypatch.setattr(cli, "connect_device", fake_connect)
    assert cli.main(["--config", str(path)]) == cli.EXIT_BAD_REQUEST


def test_device_error_exits_3(monkeypatch, tmp_path):
    def connect(config, driver):
        raise EmulatorError("MuMu did not start")

    assert run_cli(monkeypatch, tmp_path, connect=connect) == cli.EXIT_DEVICE


def test_ctrl_c_prints_finished_rounds_and_exits_130(monkeypatch, tmp_path, capsys):
    outcomes = [("18:00 - 19:00", True), ("19:00 - 20:00", KeyboardInterrupt)]

    assert run_cli(monkeypatch, tmp_path, outcomes) == cli.EXIT_INTERRUPTED
    out = capsys.readouterr().out
    assert "Summary" in out
    assert "OK   18:00 - 19:00" in out


def test_passed_start_time_exits_2_before_connecting(monkeypatch, tmp_path):
    def connect(config, driver):
        raise AssertionError("must not connect")

    monkeypatch.setattr(cli, "datetime", FixedDatetime)
    code = run_cli(monkeypatch, tmp_path, connect=connect, args=["--at", "05:00"])
    assert code == cli.EXIT_BAD_REQUEST


def test_scheduled_uses_config_start_and_clock_offset(monkeypatch, tmp_path):
    monkeypatch.setattr(cli, "datetime", FixedDatetime)
    monkeypatch.setattr(cli, "ntp_offset", lambda server: 0.25)
    run = fake_run([("18:00 - 19:00", True)])
    monkeypatch.setattr(cli, "connect_device", fake_connect)
    monkeypatch.setattr(cli, "run_booking", run)

    assert cli.main(["--config", str(tmp_path / "missing.toml"), "--scheduled"]) == 0
    assert run.kwargs["start"] == datetime(2026, 10, 8, 6, 0)
    assert run.kwargs["offset"] == 0.25


class FixedDatetime(datetime):
    @classmethod
    def now(cls, tz=None):
        return datetime(2026, 10, 8, 5, 40)  # before the default wake time, 05:45


def test_summary_is_sent_to_telegram_even_on_device_error(monkeypatch, tmp_path):
    path = tmp_path / "config.toml"
    path.write_text('telegram_token = "t"\ntelegram_chat_id = "42"\n', encoding="utf-8")
    sent = []
    monkeypatch.setattr(cli, "send_telegram", lambda token, chat, text: sent.append(text))

    def connect(config, driver):
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
    def connect(config, driver):
        raise EmulatorError("MuMu did not start")

    run_cli(monkeypatch, tmp_path, connect=connect)

    assert "Event run_finished status='failed' booked=0 total=0" in read_log(tmp_path)


def test_a_frozen_device_is_reported_then_ends_the_process(monkeypatch, tmp_path, data_home):
    ended = []
    monkeypatch.setattr(cli, "end_process", ended.append)
    error = "MuMu did not answer click within 60 s"

    def run_booking(device, config, *, results, **kwargs):
        raise DeviceNotRespondingError(error)

    monkeypatch.setattr(cli, "connect_device", fake_connect)
    monkeypatch.setattr(cli, "run_booking", run_booking)
    monkeypatch.setattr(cli, "datetime", FixedDatetime)

    code = cli.main(["--config", str(tmp_path / "missing.toml")])

    assert code == cli.EXIT_DEVICE
    assert ended == [cli.EXIT_DEVICE]
    assert f"run_finished status='failed' booked=0 total=0 error={error!r}" in read_log(tmp_path)
    assert not (data_home / "run.lock").exists()


def test_other_device_errors_end_the_process_normally(monkeypatch, tmp_path):
    ended = []
    monkeypatch.setattr(cli, "end_process", ended.append)

    def connect(config, driver):
        raise EmulatorError("MuMu did not start")

    assert run_cli(monkeypatch, tmp_path, connect=connect) == cli.EXIT_DEVICE
    assert ended == []


@pytest.mark.parametrize(
    "outcomes, args",
    [
        ([("18:00 - 19:00", True)], []),
        ([("18:00 - 19:00", False)], ["--dry-run"]),
        ([("18:00 - 19:00", KeyboardInterrupt)], []),
    ],
    ids=["real run", "dry run", "Ctrl+C"],
)
def test_the_driver_stops_after_every_run(monkeypatch, tmp_path, outcomes, args):
    devices = []

    def connect(config, driver):
        devices.append(fake_connect(config, driver))
        return devices[-1]

    run_cli(monkeypatch, tmp_path, outcomes, connect, args)

    # uiautomator2 and the other tools need UiAutomation, which the driver holds.
    assert [device.closed for device in devices] == [1]


def test_a_driver_that_does_not_stop_only_warns(monkeypatch, tmp_path):
    def connect(config, driver):
        return FakeDevice("instrumentation", OSError("adb is gone"))

    assert run_cli(monkeypatch, tmp_path, [("18:00 - 19:00", True)], connect) == cli.EXIT_OK
    assert "Could not stop the driver" in read_log(tmp_path)


def test_a_frozen_device_is_not_closed(monkeypatch, tmp_path):
    monkeypatch.setattr(cli, "end_process", lambda code: None)
    device = FakeDevice("instrumentation")

    def run_booking(device, config, *, results, **kwargs):
        raise DeviceNotRespondingError("MuMu did not answer click within 60 s")

    monkeypatch.setattr(cli, "connect_device", lambda config, driver: device)
    monkeypatch.setattr(cli, "run_booking", run_booking)
    monkeypatch.setattr(cli, "datetime", FixedDatetime)

    cli.main(["--config", str(tmp_path / "missing.toml")])

    # Each call would wait the watchdog's 60 s.
    assert device.closed == 0


def test_a_real_run_closes_mumu_after_its_rounds(monkeypatch, tmp_path, closed_mumu):
    outcomes = [("18:00 - 19:00", False), ("19:00 - 20:00", True)]

    assert run_cli(monkeypatch, tmp_path, outcomes) == cli.EXIT_ROUND_FAILED
    assert [config.mumu_index for config in closed_mumu] == [0]


@pytest.mark.parametrize(
    "outcomes, args",
    [
        ([("18:00 - 19:00", True)], ["--dry-run"]),
        ([("18:00 - 19:00", True), ("19:00 - 20:00", KeyboardInterrupt)], []),
        ([], []),
    ],
    ids=["dry run", "Ctrl+C", "no round"],
)
def test_mumu_stays_open(monkeypatch, tmp_path, closed_mumu, outcomes, args):
    run_cli(monkeypatch, tmp_path, outcomes, args=args)

    assert closed_mumu == []


def test_an_error_before_the_rounds_leaves_mumu_open(monkeypatch, tmp_path, closed_mumu):
    def run_booking(device, config, *, results, **kwargs):
        raise AppNotReadyError("The app is logged out")

    monkeypatch.setattr(cli, "connect_device", fake_connect)
    monkeypatch.setattr(cli, "run_booking", run_booking)
    monkeypatch.setattr(cli, "datetime", FixedDatetime)

    assert cli.main(["--config", str(tmp_path / "missing.toml")]) == cli.EXIT_APP_NOT_READY
    assert closed_mumu == []


def test_a_frozen_mumu_is_not_closed(monkeypatch, tmp_path, closed_mumu):
    monkeypatch.setattr(cli, "end_process", lambda code: None)

    def run_booking(device, config, *, results, **kwargs):
        results.append(RoundResult("18:00 - 19:00", False, "MuMu did not answer", 60.0))
        raise DeviceNotRespondingError("MuMu did not answer click within 60 s")

    monkeypatch.setattr(cli, "connect_device", fake_connect)
    monkeypatch.setattr(cli, "run_booking", run_booking)
    monkeypatch.setattr(cli, "datetime", FixedDatetime)

    assert cli.main(["--config", str(tmp_path / "missing.toml")]) == cli.EXIT_DEVICE
    assert closed_mumu == []


def test_without_mumu_manager_mumu_is_left_alone(monkeypatch, tmp_path, closed_mumu):
    path = tmp_path / "config.toml"
    path.write_text('mumu_manager = ""\n', encoding="utf-8")

    run_cli(monkeypatch, tmp_path, [("18:00 - 19:00", True)], args=["--config", str(path)])

    assert closed_mumu == []


def test_close_emulator_shuts_the_configured_instance_down(monkeypatch):
    shut = []

    class FakeMuMu:
        def __init__(self, manager, index):
            self.manager, self.index = manager, index

        def shutdown(self):
            shut.append((self.manager, self.index))

    monkeypatch.setattr(cli, "MuMu", FakeMuMu)

    close_emulator(Config(mumu_manager="C:/MuMu/MuMuManager.exe", mumu_index=1))

    assert shut == [(Path("C:/MuMu/MuMuManager.exe"), 1)]


def test_a_failed_close_only_warns(monkeypatch, tmp_path):
    path = tmp_path / "config.toml"
    path.write_text(f'mumu_manager = "{(tmp_path / "none.exe").as_posix()}"\n', encoding="utf-8")
    monkeypatch.setattr(cli, "close_emulator", close_emulator)

    code = run_cli(monkeypatch, tmp_path, [("18:00 - 19:00", True)], args=["--config", str(path)])

    assert code == cli.EXIT_OK
    text = read_log(tmp_path)
    assert "Closing MuMu instance 0" in text
    assert "WARNING" in text
    assert "Could not close MuMu: MuMuManager not found at" in text


def test_a_run_is_recorded_in_the_history(monkeypatch, tmp_path, data_home):
    run_cli(monkeypatch, tmp_path, [("18:00 - 19:00", True)], args=["--dry-run"])

    connection = sqlite3.connect(data_home / "booker.db")
    ((run_id, trigger, status),) = connection.execute("SELECT id, trigger, status FROM runs")
    kinds = [kind for (kind,) in connection.execute("SELECT kind FROM events ORDER BY id")]
    query = "SELECT message FROM log_lines WHERE run_id = ?"
    lines = [line for (line,) in connection.execute(query, (run_id,))]
    connection.close()
    assert (trigger, status) == ("dry_run", "ok")
    assert kinds == ["run_started", "device_ready", "run_finished"]
    assert f"court-booker {cli.__version__}" in lines
    assert "Summary" in lines


def test_the_history_stops_listening_after_the_run(monkeypatch, tmp_path):
    run_cli(monkeypatch, tmp_path, [("18:00 - 19:00", True)])

    handlers = logging.getLogger("court_booker").handlers
    assert not any(isinstance(handler, HistoryHandler) for handler in handlers)


def test_a_run_books_without_the_history(monkeypatch, tmp_path, data_home):
    data_home.parent.mkdir(parents=True, exist_ok=True)
    data_home.write_text("not a folder", encoding="utf-8")

    assert run_cli(monkeypatch, tmp_path, [("18:00 - 19:00", True)]) == cli.EXIT_OK
    assert "run not recorded" in read_log(tmp_path)


def test_a_run_waits_for_no_one_and_releases_the_lock(monkeypatch, tmp_path, data_home):
    run_cli(monkeypatch, tmp_path, [("18:00 - 19:00", True)])

    assert "Run lock taken: manual run" in read_log(tmp_path)
    assert not (data_home / "run.lock").exists()


def test_a_run_is_refused_while_another_holds_the_lock(monkeypatch, tmp_path, data_home):
    pid, started = processes.current()  # a process that is surely running
    holder = Holder(pid, started, "dry_run", "2026-10-13T10:43:10")
    data_home.mkdir(parents=True)
    (data_home / "run.lock").write_text(json.dumps(vars(holder)), encoding="utf-8")

    def connect(config, driver):
        raise AssertionError("must not touch the device")

    code = run_cli(monkeypatch, tmp_path, connect=connect, args=["--dry-run"])

    assert code == cli.EXIT_BUSY
    assert f"Another run is in progress: dry_run run (pid {pid}) since 10:43:10" in read_log(
        tmp_path
    )
    assert (data_home / "run.lock").exists()


def test_a_run_stopped_midway_ends_up_interrupted(monkeypatch, tmp_path, data_home):
    run_cli(monkeypatch, tmp_path, [("18:00 - 19:00", True)])
    connection = sqlite3.connect(data_home / "booker.db")
    with connection:
        connection.execute("UPDATE runs SET status = 'running'")  # as if the PC lost power

    run_cli(monkeypatch, tmp_path, [("18:00 - 19:00", True)])

    statuses = [status for (status,) in connection.execute("SELECT status FROM runs ORDER BY id")]
    connection.close()
    assert statuses == ["interrupted", "ok"]


def test_the_scheduled_run_may_take_the_lock_over_before_the_start(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(
        cli.RunLock,
        "acquire_for_schedule",
        lambda self, trigger, take_over_at: calls.append((trigger, take_over_at)),
    )
    monkeypatch.setattr(cli, "datetime", FixedDatetime)
    monkeypatch.setattr(cli, "ntp_offset", lambda server: 0.0)

    run_cli(monkeypatch, tmp_path, [("18:00 - 19:00", True)], args=["--scheduled"])

    assert calls == [("scheduled", datetime(2026, 10, 8, 5, 58))]


def at(hour, minute):
    """Return a datetime class whose ``now`` is 2026-10-08 at ``hour:minute``."""

    class Fixed(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 10, 8, hour, minute)

    return Fixed


def test_no_dry_run_while_the_scheduled_run_uses_the_emulator(monkeypatch, tmp_path, data_home):
    def connect(config, driver):
        raise AssertionError("must not touch the device")

    code = run_cli(monkeypatch, tmp_path, connect=connect, args=["--dry-run"], now=at(5, 55))

    assert code == cli.EXIT_BAD_REQUEST
    assert "No dry run from 05:45 to 06:05: the scheduled run uses the emulator" in read_log(
        tmp_path
    )
    assert not (data_home / "run.lock").exists()


def test_a_dry_run_may_start_once_the_scheduled_run_is_over(monkeypatch, tmp_path):
    outcomes = [("18:00 - 19:00", True)]

    assert run_cli(monkeypatch, tmp_path, outcomes, args=["--dry-run"], now=at(6, 5)) == 0


def test_a_manual_run_is_not_held_to_the_window(monkeypatch, tmp_path):
    outcomes = [("18:00 - 19:00", True)]

    assert run_cli(monkeypatch, tmp_path, outcomes, now=at(5, 55)) == cli.EXIT_OK


CHECKS = [
    Check("mumu_installed", Status.OK, "MuMu at C:/MuMu/MuMuManager.exe"),
    Check("app_installed", Status.USER, "com.vinhomes.resident is not installed in MuMu"),
]


def run_setup(monkeypatch, tmp_path, args=(), now=None, results=None):
    """Run ``court-booker setup`` with fake checks; returns the exit code and auto setup calls."""
    calls = []

    def fake_auto_setup(config, config_path, tools, *, restart_mumu=False, run=None):
        calls.append(restart_mumu)
        return results or [Check("wake_timers", Status.FIXED, "enabled")]

    monkeypatch.setattr(cli, "datetime", now or FixedDatetime)
    monkeypatch.setattr(cli, "find_tools", lambda config: None)
    monkeypatch.setattr(cli, "run_checks", lambda config, tools: CHECKS)
    monkeypatch.setattr(device_setup, "auto_setup", fake_auto_setup)
    code = cli.main(["setup", "--config", str(tmp_path / "missing.toml"), *args])
    return code, calls


def test_setup_prints_every_item(monkeypatch, tmp_path, capsys):
    code, calls = run_setup(monkeypatch, tmp_path)

    out = capsys.readouterr().out
    assert code == 1  # the app still has to be installed by the user
    assert "ok       mumu_installed  MuMu at C:/MuMu/MuMuManager.exe" in out
    assert "user     app_installed   com.vinhomes.resident is not installed" in out
    assert calls == []


def test_auto_setup_is_recorded_as_setup_steps(monkeypatch, tmp_path, data_home):
    code, calls = run_setup(monkeypatch, tmp_path, ["--auto", "--restart-mumu"])

    connection = sqlite3.connect(data_home / "booker.db")
    steps = connection.execute("SELECT run_id, category, kind FROM events ORDER BY id").fetchall()
    connection.close()
    assert code == cli.EXIT_OK
    assert calls == [True]
    assert steps == [
        (None, "setup", "setup_started"),
        (None, "setup", "setup_item"),
        (None, "setup", "setup_finished"),
    ]
    assert not (data_home / "run.lock").exists()


def test_auto_setup_waits_for_no_run(monkeypatch, tmp_path, data_home):
    pid, started = processes.current()
    data_home.mkdir(parents=True)
    holder = Holder(pid, started, "dry_run", "2026-10-13T10:43:10")
    (data_home / "run.lock").write_text(json.dumps(vars(holder)), encoding="utf-8")

    code, calls = run_setup(monkeypatch, tmp_path, ["--auto"])

    assert code == cli.EXIT_BUSY
    assert calls == []


def test_no_auto_setup_while_the_scheduled_run_uses_the_emulator(monkeypatch, tmp_path):
    code, calls = run_setup(monkeypatch, tmp_path, ["--auto"], now=at(5, 50))

    assert code == cli.EXIT_BAD_REQUEST
    assert calls == []


def test_serve_explains_a_missing_app_extra(monkeypatch, capsys):
    monkeypatch.setitem(sys.modules, "court_booker.api.server", None)

    assert cli.main(["serve"]) == cli.EXIT_BAD_REQUEST
    assert "The backend needs the app extra" in capsys.readouterr().out


def test_a_run_does_not_load_the_backend():
    code = "import sys, court_booker.cli; print('fastapi' in sys.modules)"
    src = str(Path(cli.__file__).resolve().parents[1])
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": src},
        check=True,
    )

    assert result.stdout.strip() == "False"


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
