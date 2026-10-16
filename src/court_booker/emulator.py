"""Start the MuMu Player emulator through its ``MuMuManager.exe`` command line."""

from __future__ import annotations

import json
import logging
import subprocess
import time
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Callable

from court_booker.errors import EmulatorError

logger = logging.getLogger(__name__)

Run = Callable[[Sequence[str]], "subprocess.CompletedProcess[str]"]

_POLL_INTERVAL = 2.0
_COMMAND_TIMEOUT = 60.0
# Keep the console window of a scheduled run from flashing for every call.
_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def run_command(args: Sequence[str]) -> subprocess.CompletedProcess[str]:
    """Run ``args`` and capture its text output."""
    return subprocess.run(
        list(args),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=_COMMAND_TIMEOUT,
        creationflags=_NO_WINDOW,
        check=False,
    )


class MuMu:
    """One MuMu Player instance, addressed by its index."""

    def __init__(
        self,
        manager: Path,
        index: int = 0,
        run: Run = run_command,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.manager = manager
        self.index = index
        self._run = run
        self._clock = clock
        self._sleep = sleep

    def info(self) -> dict[str, Any]:
        """Return the instance state reported by ``MuMuManager.exe info``."""
        output = self._call("info")
        try:
            data = json.loads(output)
        except ValueError as exc:
            raise EmulatorError(f"Unexpected output from MuMuManager info: {output!r}") from exc
        # A single index returns the instance itself; several indexes are keyed by index.
        if isinstance(data, dict) and "index" not in data and str(self.index) in data:
            data = data[str(self.index)]
        if not isinstance(data, dict):
            raise EmulatorError(f"Unexpected output from MuMuManager info: {output!r}")
        return data

    def is_started(self) -> bool:
        """Return whether Android inside the instance has finished booting."""
        return bool(self.info().get("is_android_started"))

    def adb_serial(self) -> str | None:
        """Return the ``host:port`` ADB serial of the running instance, if reported."""
        info = self.info()
        host, port = info.get("adb_host_ip"), info.get("adb_port")
        return f"{host}:{port}" if host and port else None

    def launch(self) -> None:
        """Ask MuMu to start the instance; returns before Android has booted."""
        self._call("control", "launch")

    def restart(self) -> None:
        """Ask MuMu to restart the instance; returns before Android has booted."""
        self._call("control", "restart")

    def shutdown(self) -> None:
        """Ask MuMu to shut the instance down."""
        self._call("control", "shutdown")

    def settings(self, *keys: str) -> dict[str, str]:
        """Return the instance settings named ``keys``; readable while the instance is off."""
        output = self._call("setting", *[arg for key in keys for arg in ("-k", key)])
        try:
            data = json.loads(output)
        except ValueError as exc:
            raise EmulatorError(f"Unexpected output from MuMuManager setting: {output!r}") from exc
        if not isinstance(data, dict):
            raise EmulatorError(f"Unexpected output from MuMuManager setting: {output!r}")
        return {str(key): str(value) for key, value in data.items()}

    def change_settings(self, values: Mapping[str, str]) -> None:
        """Write instance settings; screen settings apply when the instance starts next."""
        self._call(
            "setting", *[arg for key, value in values.items() for arg in ("-k", key, "-val", value)]
        )

    def ensure_started(self, timeout: float) -> None:
        """Launch the instance unless running, then wait until Android has booted."""
        if self.is_started():
            logger.info("MuMu instance %d already running", self.index)
            return
        logger.info("Launching MuMu instance %d", self.index)
        started = self._clock()
        self.launch()
        while self._clock() - started < timeout:
            self._sleep(_POLL_INTERVAL)
            if self.is_started():
                logger.info("Android started after %.1f s", self._clock() - started)
                return
        raise EmulatorError(f"MuMu instance {self.index} did not finish booting in {timeout:.0f} s")

    def _call(self, command: str, *args: str) -> str:
        if not self.manager.is_file():
            raise EmulatorError(
                f"MuMuManager not found at {self.manager}; set 'mumu_manager' in config.toml, "
                "or leave it empty to skip starting the emulator"
            )
        argv = [str(self.manager), command, "-v", str(self.index), *args]
        try:
            result = self._run(argv)
        except (OSError, subprocess.SubprocessError) as exc:
            raise EmulatorError(f"MuMuManager {command} failed: {exc}") from exc
        if result.returncode != 0:
            detail = (result.stderr or result.stdout).strip()
            raise EmulatorError(f"MuMuManager {command} exited with {result.returncode}: {detail}")
        return result.stdout
