"""MuMu control tests with a fake MuMuManager; no emulator required."""

import json
import subprocess

import pytest

from court_booker.emulator import MuMu
from court_booker.errors import EmulatorError

RUNNING = {
    "index": "0",
    "is_android_started": True,
    "adb_host_ip": "127.0.0.1",
    "adb_port": 16384,
}
STOPPED = {"index": "0", "is_android_started": False}


class FakeManager:
    """Records calls; Android reports started after ``boot_polls`` info calls post-launch."""

    def __init__(self, started=False, boot_polls=2, keyed=False):
        self.calls = []
        self.started = started
        self.boot_polls = boot_polls
        self.keyed = keyed
        self.now = 0.0

    def run(self, argv):
        command = argv[1]
        self.calls.append(command)
        if command == "control":
            self.launched_at = len(self.calls)
            return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")
        if not self.started and "control" in self.calls:
            polls_since_launch = len(self.calls) - self.launched_at
            self.started = polls_since_launch >= self.boot_polls
        state = RUNNING if self.started else STOPPED
        data = {"0": state} if self.keyed else state
        return subprocess.CompletedProcess(argv, 0, stdout=json.dumps(data), stderr="")

    def sleep(self, seconds):
        self.now += seconds


@pytest.fixture
def manager_path(tmp_path):
    path = tmp_path / "MuMuManager.exe"
    path.write_bytes(b"")
    return path


def make(manager_path, fake):
    return MuMu(manager_path, 0, run=fake.run, clock=lambda: fake.now, sleep=fake.sleep)


def test_running_instance_is_not_launched(manager_path):
    fake = FakeManager(started=True)
    make(manager_path, fake).ensure_started(timeout=180)
    assert fake.calls == ["info"]


def test_stopped_instance_is_launched_and_awaited(manager_path):
    fake = FakeManager(boot_polls=3)
    make(manager_path, fake).ensure_started(timeout=180)
    assert fake.calls == ["info", "control", "info", "info", "info"]


def test_boot_timeout_raises(manager_path):
    fake = FakeManager(boot_polls=1000)
    with pytest.raises(EmulatorError, match="did not finish booting"):
        make(manager_path, fake).ensure_started(timeout=10)


def test_adb_serial_from_keyed_info(manager_path):
    fake = FakeManager(started=True, keyed=True)
    assert make(manager_path, fake).adb_serial() == "127.0.0.1:16384"


def test_missing_manager_explains_the_setting(tmp_path):
    mumu = MuMu(tmp_path / "missing.exe", run=FakeManager().run)
    with pytest.raises(EmulatorError, match="mumu_manager"):
        mumu.is_started()


class SettingManager:
    """Answers ``setting`` like MuMuManager: JSON of the asked keys; records every call."""

    def __init__(self, values):
        self.values = dict(values)
        self.calls = []

    def run(self, argv):
        self.calls.append(argv[1:])
        args = argv[4:]
        if "-val" in args:
            pairs = zip(args[1::4], args[3::4])
            self.values.update(pairs)
            output = ""
        else:
            output = json.dumps({key: self.values[key] for key in args[1::2]})
        return subprocess.CompletedProcess(argv, 0, stdout=output, stderr="")


def test_settings_are_read_by_key(manager_path):
    fake = SettingManager({"resolution_width": "540.000000", "resolution_dpi": "220.000000"})

    values = MuMu(manager_path, run=fake.run).settings("resolution_width", "resolution_dpi")

    assert values == {"resolution_width": "540.000000", "resolution_dpi": "220.000000"}
    assert fake.calls == [["setting", "-v", "0", "-k", "resolution_width", "-k", "resolution_dpi"]]


def test_settings_are_written_as_key_value_pairs(manager_path):
    fake = SettingManager({})

    MuMu(manager_path, run=fake.run).change_settings({"resolution_mode": "custom", "x": "1"})

    assert fake.calls == [
        ["setting", "-v", "0", "-k", "resolution_mode", "-val", "custom", "-k", "x", "-val", "1"]
    ]
    assert fake.values == {"resolution_mode": "custom", "x": "1"}


def test_unreadable_settings_raise(manager_path):
    def run(argv):
        return subprocess.CompletedProcess(argv, 0, stdout="no json", stderr="")

    with pytest.raises(EmulatorError, match="setting"):
        MuMu(manager_path, run=run).settings("resolution_dpi")


def test_restart_asks_mumu(manager_path):
    fake = FakeManager(started=True)

    make(manager_path, fake).restart()

    assert fake.calls == ["control"]


def test_shutdown_asks_mumu_to_shut_the_instance_down(manager_path):
    calls = []

    def run(argv):
        calls.append(argv)
        return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")

    MuMu(manager_path, 1, run=run).shutdown()

    assert calls == [[str(manager_path), "control", "-v", "1", "shutdown"]]


def test_failed_command_raises(manager_path):
    def run(argv):
        return subprocess.CompletedProcess(argv, 1, stdout="", stderr="no such player")

    with pytest.raises(EmulatorError, match="no such player"):
        MuMu(manager_path, run=run).is_started()
