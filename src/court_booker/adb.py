"""Find ``adb``, make sure its server runs, and connect to the emulator."""

from __future__ import annotations

import logging
import shutil
import socket
import subprocess
import time
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Callable

from court_booker.emulator import Run, run_command
from court_booker.errors import (
    AdbNotFoundError,
    DeviceConnectionError,
    MultipleDevicesError,
    NoDeviceError,
)

logger = logging.getLogger(__name__)

Probe = Callable[[str, int], bool]

AUTO = "auto"
LOCALHOST = "127.0.0.1"
SERVER_PORT = 5037
# MuMu 6 (7555) and MuMu 12 instances 0-2, LDPlayer/BlueStacks, Nox.
EMULATOR_PORTS = (7555, 16384, 16416, 16448, 5555, 5557, 5559, 62001)
CONNECT_TIMEOUT = 30.0
_RETRY_INTERVAL = 1.0
_PROBE_TIMEOUT = 0.3


def port_open(host: str, port: int) -> bool:
    """Return whether something accepts TCP connections on ``host:port``."""
    try:
        with socket.create_connection((host, port), timeout=_PROBE_TIMEOUT):
            return True
    except OSError:
        return False


def find_adb(
    adb_path: str = "",
    extra_dirs: Iterable[Path] = (),
    which: Callable[[str], str | None] = shutil.which,
) -> Path:
    """Return the adb executable: ``adb_path``, else ``PATH``, else one in ``extra_dirs``."""
    if adb_path:
        path = Path(adb_path)
        if path.is_file():
            return path
        raise AdbNotFoundError(f"adb_path {adb_path!r} in config.toml does not exist")
    found = which("adb")
    if found:
        return Path(found)
    for directory in extra_dirs:
        for name in ("adb.exe", "adb"):
            if (directory / name).is_file():
                return directory / name
    raise AdbNotFoundError(
        "adb not found; install Google platform-tools and add it to PATH, "
        "or set 'adb_path' in config.toml"
    )


class Adb:
    """Thin wrapper over the adb command line."""

    def __init__(
        self,
        path: Path,
        run: Run = run_command,
        probe: Probe = port_open,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.path = path
        self._run = run
        self._probe = probe
        self._clock = clock
        self._sleep = sleep

    def ensure_server(self) -> None:
        """Reuse a running adb server, or start one."""
        if self._probe(LOCALHOST, SERVER_PORT):
            logger.debug("Reusing the adb server on port %d", SERVER_PORT)
            return
        logger.info("Starting the adb server")
        self._call("start-server")

    def devices(self) -> list[str]:
        """Return the serials of devices that are online."""
        serials = []
        for line in self._call("devices").splitlines():
            serial, _, state = line.partition("\t")
            if state.strip() == "device":
                serials.append(serial.strip())
        return serials

    def connect(self, serial: str) -> bool:
        """Run ``adb connect`` and return whether it reported success."""
        output = self._call("connect", serial)
        # Success prints "connected to" or "already connected to"; failures do not.
        return "connected to" in output

    def connect_until(self, serial: str, timeout: float = CONNECT_TIMEOUT) -> str:
        """Connect ``serial``, retrying while the device is still starting."""
        deadline = self._clock() + timeout
        while True:
            if serial in self.devices():
                return serial
            if ":" in serial and self.connect(serial) and serial in self.devices():
                logger.info("Connected to %s", serial)
                return serial
            if self._clock() >= deadline:
                raise DeviceConnectionError(f"Could not connect to {serial} in {timeout:.0f} s")
            self._sleep(_RETRY_INTERVAL)

    def shell(self, serial: str, *args: str) -> str:
        """Run ``adb -s serial shell args`` and return its output."""
        return self._call("-s", serial, "shell", *args)

    def forward(self, serial: str, remote: str) -> int:
        """Return a local TCP port forwarded to ``remote`` on ``serial``, reusing one if set."""
        for line in self._call("forward", "--list").splitlines():
            parts = line.split()
            if len(parts) == 3 and parts[0] == serial and parts[2] == remote:
                kind, _, port = parts[1].partition(":")
                if kind == "tcp" and port.isdigit():
                    return int(port)
        output = self._call("-s", serial, "forward", "tcp:0", remote).strip()
        if not output.isdigit():
            raise DeviceConnectionError(f"adb forward to {remote} failed: {output or 'no port'}")
        return int(output)

    def forward_remove(self, serial: str, port: int) -> None:
        """Drop the forward of local TCP ``port``."""
        self._call("-s", serial, "forward", "--remove", f"tcp:{port}")

    def install(self, serial: str, apk: Path) -> str:
        """Install or update ``apk`` and return what adb printed, errors included."""
        try:
            result = self._run([str(self.path), "-s", serial, "install", "-r", str(apk)])
        except (OSError, subprocess.SubprocessError) as exc:
            raise DeviceConnectionError(f"adb install failed: {exc}") from exc
        return result.stdout + result.stderr

    def discover(self, ports: Sequence[int] = EMULATOR_PORTS) -> list[str]:
        """Return online devices, connecting the first open emulator port if none is."""
        serials = self.devices()
        if serials:
            return serials
        for port in ports:
            if not self._probe(LOCALHOST, port):
                continue
            serial = f"{LOCALHOST}:{port}"
            if self.connect(serial):
                logger.info("Found emulator at %s", serial)
                break
        return self.devices()

    def _call(self, *args: str) -> str:
        try:
            result = self._run([str(self.path), *args])
        except (OSError, subprocess.SubprocessError) as exc:
            raise DeviceConnectionError(f"adb {args[0]} failed: {exc}") from exc
        return result.stdout


def resolve_device(adb: Adb, device: str, preferred: str | None = None) -> str:
    """Return the serial to drive.

    An explicit ``device`` is connected alone. ``auto`` uses ``preferred`` (the
    serial reported by the emulator) when known, else scans for a single device.
    """
    adb.ensure_server()
    if device != AUTO:
        return adb.connect_until(device)
    if preferred:
        return adb.connect_until(preferred)
    serials = adb.discover()
    if not serials:
        raise NoDeviceError("No emulator found; start it or set 'device' in config.toml")
    # MuMu also shows up as "emulator-5554" next to its host:port serial; prefer the latter.
    networked = [serial for serial in serials if ":" in serial]
    if len(networked) == 1:
        return networked[0]
    if len(serials) > 1:
        raise MultipleDevicesError(serials)
    return serials[0]
