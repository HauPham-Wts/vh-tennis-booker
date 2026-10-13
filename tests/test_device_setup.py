"""Tests for the device setup checks and auto setup, with fake tools."""

import subprocess
import sys
from pathlib import Path

import pytest

from court_booker import device_setup
from court_booker.device_setup import Status
from court_booker.errors import DeviceConnectionError


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
