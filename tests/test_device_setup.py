"""Tests for the device setup checks and auto setup, with fake tools."""

import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pytest

from court_booker import device_setup
from court_booker.config import Config, load_config
from court_booker.device_setup import Status, Tools
from court_booker.errors import DeviceConnectionError, RequestError
from court_booker.events import EventKind, MemorySink, Reporter


def install_mumu(folder, layout=("nx_main", "MuMuManager.exe")):
    manager = folder.joinpath(*layout)
    manager.parent.mkdir(parents=True)
    manager.write_bytes(b"")
    return manager


def test_the_configured_manager_comes_first(tmp_path):
    manager = install_mumu(tmp_path / "custom")
    other = install_mumu(tmp_path / "Netease")

    assert device_setup.find_mumu_manager(str(manager), [other.parent.parent]) == manager


def test_the_manager_is_found_in_an_install_folder(tmp_path):
    manager = install_mumu(tmp_path / "MuMuPlayer")

    found = device_setup.find_mumu_manager(
        "C:/missing.exe", [tmp_path / "none", tmp_path / "MuMuPlayer"]
    )

    assert found == manager


def test_an_older_layout_is_found(tmp_path):
    manager = install_mumu(tmp_path / "MuMu Player 12", ("shell", "MuMuManager.exe"))

    assert device_setup.find_mumu_manager("", [tmp_path / "MuMu Player 12"]) == manager


def test_no_mumu_is_found(tmp_path):
    assert device_setup.find_mumu_manager("", [tmp_path]) is None


@pytest.mark.skipif(sys.platform != "win32", reason="the uninstall registry is Windows only")
def test_registry_folders_are_paths():
    assert all(isinstance(folder, Path) for folder in device_setup.installed_folders())


class FakeMuMu:
    """A MuMu instance with settings, a running state and an installed package list."""

    def __init__(self, settings=None, started=True, packages=("com.vinhomes.resident",)):
        self.values = dict(
            settings
            or {
                "resolution_width": "540.000000",
                "resolution_height": "1600.000000",
                "resolution_dpi": "220.000000",
            }
        )
        self.started = started
        self.packages = packages
        self.changed = []
        self.restarts = 0

    def settings(self, *keys):
        return {key: self.values[key] for key in keys if key in self.values}

    def change_settings(self, values):
        self.changed.append(dict(values))
        self.values.update(values)

    def is_started(self):
        return self.started

    def restart(self):
        self.restarts += 1

    def adb_serial(self):
        return "127.0.0.1:16384"


def screen(width, height, dpi):
    return {
        "resolution_width": f"{width}.000000",
        "resolution_height": f"{height}.000000",
        "resolution_dpi": f"{dpi}.000000",
    }


def test_screen_check():
    assert device_setup.check_screen(FakeMuMu()).status is Status.OK
    wrong = device_setup.check_screen(FakeMuMu(screen(540, 960, 240)))
    assert wrong.status is Status.FIXABLE
    assert "540x960 at 240 DPI" in wrong.detail
    assert device_setup.check_screen(None).status is Status.UNKNOWN
    assert device_setup.check_screen(FakeMuMu({"resolution_width": "x"})).status is Status.UNKNOWN


POWERCFG = """Power Scheme GUID: bfe96730-c015-4cfa-b549-ec3c64ca0e05  (Ultimate Performance)
  Subgroup GUID: 238c9fa8-0aad-41ed-83f4-97be242c8f20  (Sleep)
    GUID Alias: SUB_SLEEP
    Power Setting GUID: bd3b718a-0680-4d9d-8ab2-e1d2b4ac806d  (Allow wake timers)
      GUID Alias: RTCWAKE
      Possible Setting Index: 000
      Possible Setting Friendly Name: Disable
      Possible Setting Index: 001
      Possible Setting Friendly Name: Enable
      Possible Setting Index: 002
      Possible Setting Friendly Name: Important Wake Timers Only
    Current AC Power Setting Index: 0x{ac:08x}
    Current DC Power Setting Index: 0x{dc:08x}
"""


class FakePowercfg:
    """Answers ``powercfg /query`` and records ``/set...valueindex`` and ``/setactive``."""

    def __init__(self, ac=1, dc=1, returncode=0):
        self.ac, self.dc = ac, dc
        self.returncode = returncode
        self.calls = []

    def run(self, argv):
        self.calls.append(argv[1:])
        if argv[1] == "/setacvalueindex":
            self.ac = int(argv[-1])
        elif argv[1] == "/setdcvalueindex":
            self.dc = int(argv[-1])
        output = POWERCFG.format(ac=self.ac, dc=self.dc) if argv[1] == "/query" else ""
        return subprocess.CompletedProcess(argv, self.returncode, stdout=output, stderr="")


def test_wake_timer_values_are_read_by_position():
    assert device_setup.wake_timer_indexes(POWERCFG.format(ac=1, dc=2)) == (1, 2)
    assert device_setup.wake_timer_indexes("Invalid Parameters") is None


def test_wake_timer_check():
    assert device_setup.check_wake_timers(FakePowercfg().run).status is Status.OK
    battery_off = device_setup.check_wake_timers(FakePowercfg(dc=0).run)
    assert battery_off.status is Status.FIXABLE
    assert battery_off.detail == "Wake timers enabled plugged in, disabled on battery"
    assert device_setup.check_wake_timers(FakePowercfg(returncode=1).run).status is Status.UNKNOWN


def test_wake_timer_check_without_powercfg():
    def missing(argv):
        raise FileNotFoundError("powercfg")

    assert device_setup.check_wake_timers(missing).status is Status.UNKNOWN


class FakeAdb:
    """The adb of a running MuMu with ``packages`` installed."""

    def __init__(self, packages=("com.vinhomes.resident",), fail=False):
        self.packages = packages
        self.fail = fail

    def ensure_server(self):
        pass

    def connect_until(self, serial):
        if self.fail:
            raise DeviceConnectionError(f"Could not connect to {serial}")
        return serial

    def shell(self, serial, *args):
        package = args[-1]
        return f"package:/data/app/{package}/base.apk\n" if package in self.packages else ""


def test_app_check():
    package = "com.vinhomes.resident"

    assert device_setup.check_app(FakeMuMu(), FakeAdb(), package).status is Status.OK
    assert device_setup.check_app(FakeMuMu(), FakeAdb(()), package).status is Status.USER
    stopped = device_setup.check_app(FakeMuMu(started=False), FakeAdb(), package)
    assert stopped.status is Status.UNKNOWN
    assert stopped.detail == "Start MuMu to check the app"
    offline = device_setup.check_app(FakeMuMu(), FakeAdb(fail=True), package)
    assert offline.status is Status.UNKNOWN
    assert device_setup.check_app(None, None, package).status is Status.UNKNOWN


def test_mumu_check(tmp_path):
    manager = install_mumu(tmp_path)

    assert device_setup.check_mumu(None, "").status is Status.USER
    assert device_setup.check_mumu(manager, "").status is Status.FIXABLE
    assert device_setup.check_mumu(manager, "C:/elsewhere.exe").status is Status.FIXABLE
    assert device_setup.check_mumu(manager, str(manager)).status is Status.OK


def tools_for(tmp_path, mumu=None, adb=None):
    manager = install_mumu(tmp_path / "MuMuPlayer")
    return Tools(manager, mumu or FakeMuMu(), adb or FakeAdb())


def config_for(tools):
    return Config(mumu_manager=str(tools.manager))


def statuses(results):
    return {result.item: result.status for result in results}


def test_checks_cover_every_item(tmp_path):
    tools = tools_for(tmp_path)

    results = device_setup.run_checks(config_for(tools), tools, FakePowercfg().run)

    assert statuses(results) == {
        device_setup.MUMU_INSTALLED: Status.OK,
        device_setup.MUMU_SCREEN: Status.OK,
        device_setup.WAKE_TIMERS: Status.OK,
        device_setup.APP_INSTALLED: Status.OK,
    }


def test_auto_setup_changes_nothing_that_is_right(tmp_path):
    tools = tools_for(tmp_path)
    powercfg = FakePowercfg()
    config_path = tmp_path / "config.toml"

    results = device_setup.auto_setup(config_for(tools), config_path, tools, run=powercfg.run)

    assert set(statuses(results).values()) == {Status.OK}
    assert tools.mumu.changed == []
    assert [call[0] for call in powercfg.calls] == ["/query"]
    assert not config_path.exists()


def test_auto_setup_saves_the_mumu_path(tmp_path):
    tools = tools_for(tmp_path)
    config_path = tmp_path / "config.toml"

    results = device_setup.auto_setup(
        Config(mumu_manager=""), config_path, tools, run=FakePowercfg().run
    )

    assert statuses(results)[device_setup.MUMU_INSTALLED] is Status.FIXED
    assert load_config(config_path).mumu_manager == str(tools.manager)


def test_auto_setup_sets_the_screen_of_a_stopped_mumu(tmp_path):
    mumu = FakeMuMu(screen(540, 960, 240), started=False)
    tools = tools_for(tmp_path, mumu)

    results = device_setup.auto_setup(
        config_for(tools), tmp_path / "c.toml", tools, run=FakePowercfg().run
    )

    screen_result = results[1]
    assert screen_result.status is Status.FIXED
    assert screen_result.detail.endswith("applies when MuMu starts")
    assert mumu.changed == [device_setup.SCREEN_SETTINGS]
    assert mumu.restarts == 0


def test_a_running_mumu_is_restarted_only_when_allowed(tmp_path):
    mumu = FakeMuMu(screen(540, 960, 240))
    tools = tools_for(tmp_path, mumu)
    config = config_for(tools)

    asked = device_setup.auto_setup(config, tmp_path / "c.toml", tools, run=FakePowercfg().run)
    assert asked[1].status is Status.FIXABLE
    assert mumu.changed == []

    done = device_setup.auto_setup(
        config, tmp_path / "c.toml", tools, restart_mumu=True, run=FakePowercfg().run
    )
    assert done[1].status is Status.FIXED
    assert mumu.restarts == 1


def test_auto_setup_allows_wake_timers(tmp_path):
    tools = tools_for(tmp_path)
    powercfg = FakePowercfg(ac=0, dc=2)

    results = device_setup.auto_setup(
        config_for(tools), tmp_path / "c.toml", tools, run=powercfg.run
    )

    assert statuses(results)[device_setup.WAKE_TIMERS] is Status.FIXED
    assert ["/setacvalueindex", "SCHEME_CURRENT", "SUB_SLEEP", "RTCWAKE", "1"] in powercfg.calls
    assert ["/setdcvalueindex", "SCHEME_CURRENT", "SUB_SLEEP", "RTCWAKE", "1"] in powercfg.calls
    assert ["/setactive", "SCHEME_CURRENT"] in powercfg.calls


def test_wake_timers_refused_by_windows_need_the_user(tmp_path):
    tools = tools_for(tmp_path)
    powercfg = FakePowercfg(dc=0)

    def run(argv):
        result = powercfg.run(argv)
        if argv[1] != "/query":
            return subprocess.CompletedProcess(argv, 1, stdout="", stderr="Access denied.")
        return result

    results = device_setup.auto_setup(config_for(tools), tmp_path / "c.toml", tools, run=run)

    wake = results[2]
    assert wake.status is Status.USER
    assert "Access denied." in wake.detail


def test_run_auto_setup_holds_the_lock_and_reports_each_item(tmp_path):
    tools = tools_for(tmp_path)
    sink = MemorySink()
    lock_path = tmp_path / "run.lock"
    seen = []

    def run(argv):
        seen.append(lock_path.exists())
        return FakePowercfg().run(argv)

    results = device_setup.run_auto_setup(
        config_for(tools),
        tmp_path / "c.toml",
        tools,
        lock_path,
        Reporter(sink),
        now=datetime(2026, 10, 13, 14, 0),
        run=run,
    )

    assert len(results) == 4
    assert all(seen)  # powercfg ran while the lock was held
    assert not lock_path.exists()
    assert sink.kinds == [
        EventKind.SETUP_STARTED,
        *[EventKind.SETUP_ITEM] * 4,
        EventKind.SETUP_FINISHED,
    ]
    assert sink.events[-1].data == {"left": [], "error": None}


def test_run_auto_setup_waits_for_the_scheduled_run(tmp_path):
    tools = tools_for(tmp_path)

    with pytest.raises(RequestError, match="No auto setup from 05:45 to 06:05"):
        device_setup.run_auto_setup(
            config_for(tools),
            tmp_path / "c.toml",
            tools,
            tmp_path / "run.lock",
            Reporter(MemorySink()),
            now=datetime(2026, 10, 14, 5, 50),
        )
