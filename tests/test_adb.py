"""ADB discovery tests with a fake adb and port probe; no adb or network required."""

import subprocess

import pytest

from court_booker.adb import Adb, find_adb, resolve_device
from court_booker.errors import (
    AdbNotFoundError,
    DeviceConnectionError,
    MultipleDevicesError,
    NoDeviceError,
)


class FakeAdb:
    """Simulates the adb server: ``reachable`` serials connect, ``attached`` are online."""

    def __init__(self, attached=(), reachable=(), open_ports=(), server_running=True):
        self.attached = list(attached)
        self.reachable = set(reachable)
        self.open_ports = set(open_ports)
        self.server_running = server_running
        self.calls = []
        self.probed = []
        self.now = 0.0

    def run(self, argv):
        args = argv[1:]
        self.calls.append(" ".join(args))
        stdout = ""
        if args[0] == "devices":
            lines = ["List of devices attached", *(f"{s}\tdevice" for s in self.attached)]
            stdout = "\n".join(lines) + "\n"
        elif args[0] == "connect":
            serial = args[1]
            if serial in self.reachable:
                if serial not in self.attached:
                    self.attached.append(serial)
                stdout = f"connected to {serial}\n"
            else:
                stdout = f"cannot connect to {serial}: refused\n"
        elif args[0] == "start-server":
            self.server_running = True
        return subprocess.CompletedProcess(argv, 0, stdout=stdout, stderr="")

    def probe(self, host, port):
        self.probed.append(port)
        if port == 5037:
            return self.server_running
        return port in self.open_ports

    def sleep(self, seconds):
        self.now += seconds

    def adb(self):
        return Adb("adb", run=self.run, probe=self.probe, clock=lambda: self.now, sleep=self.sleep)


def test_running_server_is_reused():
    fake = FakeAdb(attached=["127.0.0.1:16384"])
    resolve_device(fake.adb(), "auto")
    assert "start-server" not in fake.calls


def test_missing_server_is_started():
    fake = FakeAdb(attached=["127.0.0.1:16384"], server_running=False)
    resolve_device(fake.adb(), "auto")
    assert fake.calls[0] == "start-server"


def test_explicit_serial_is_connected_without_scan():
    fake = FakeAdb(reachable=["127.0.0.1:7555"], open_ports=[16384])
    assert resolve_device(fake.adb(), "127.0.0.1:7555") == "127.0.0.1:7555"
    assert fake.probed == [5037]


def test_explicit_serial_that_never_connects_raises():
    fake = FakeAdb()
    with pytest.raises(DeviceConnectionError, match=r"127\.0\.0\.1:7555"):
        resolve_device(fake.adb(), "127.0.0.1:7555")
    assert fake.now >= 30


def test_auto_prefers_the_emulator_serial():
    fake = FakeAdb(attached=["emulator-5554"], reachable=["127.0.0.1:16384"])
    assert resolve_device(fake.adb(), "auto", preferred="127.0.0.1:16384") == "127.0.0.1:16384"


def test_auto_scans_open_ports_only():
    fake = FakeAdb(reachable=["127.0.0.1:5555"], open_ports=[5555])
    assert resolve_device(fake.adb(), "auto") == "127.0.0.1:5555"
    connects = [call for call in fake.calls if call.startswith("connect")]
    assert connects == ["connect 127.0.0.1:5555"]


def test_auto_without_devices_raises():
    with pytest.raises(NoDeviceError):
        resolve_device(FakeAdb().adb(), "auto")


def test_auto_with_several_devices_lists_them():
    fake = FakeAdb(attached=["127.0.0.1:7555", "127.0.0.1:5555"])
    with pytest.raises(MultipleDevicesError) as info:
        resolve_device(fake.adb(), "auto")
    assert info.value.serials == ["127.0.0.1:7555", "127.0.0.1:5555"]


def test_auto_ignores_emulator_alias_of_networked_serial():
    fake = FakeAdb(attached=["127.0.0.1:7555", "emulator-5554"])
    assert resolve_device(fake.adb(), "auto") == "127.0.0.1:7555"


def test_find_adb_order(tmp_path):
    bundled = tmp_path / "adb.exe"
    bundled.write_bytes(b"")
    assert find_adb("", [tmp_path], which=lambda name: "C:/tools/adb.exe").as_posix() == (
        "C:/tools/adb.exe"
    )
    assert find_adb("", [tmp_path], which=lambda name: None) == bundled
    assert find_adb(str(bundled), [], which=lambda name: None) == bundled


def test_find_adb_missing_explains_fix(tmp_path):
    with pytest.raises(AdbNotFoundError, match="adb_path"):
        find_adb("", [tmp_path], which=lambda name: None)
    with pytest.raises(AdbNotFoundError, match="does not exist"):
        find_adb(str(tmp_path / "nope.exe"))


def test_shell_runs_on_the_given_device():
    fake = FakeAdb(attached=["127.0.0.1:16384"])

    fake.adb().shell("127.0.0.1:16384", "pm", "path", "com.vinhomes.resident")

    assert fake.calls == ["-s 127.0.0.1:16384 shell pm path com.vinhomes.resident"]
