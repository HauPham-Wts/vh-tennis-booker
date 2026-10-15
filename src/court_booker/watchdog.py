"""A time limit on every command sent to the device.

MuMu froze twice on 2026-10-13, and a run then waited inside a uiautomator2 call for good:
it logged nothing more until Task Scheduler ended it an hour later. Device calls therefore
run on a worker thread, and the run stops waiting for one after :data:`COMMAND_TIMEOUT`.
The run then ends like any device failure: logged, in the history, the lock released, exit
code 3. Nothing tries to rescue it, since a frozen emulator has lost the race already.
"""

from __future__ import annotations

import queue
import threading
from typing import Any, Callable, TypeVar

from court_booker.errors import DeviceNotRespondingError

T = TypeVar("T")

COMMAND_TIMEOUT = 60.0
"""Seconds a device command may take. Normal ones take well under a second (a screen read
69 ms at 06:00); uiautomator2 gives up on a request after 10 s and restarts its server, which
fits in this limit too. Waits for a screen are many short commands, each with this limit."""
_WAKE_SECONDS = 0.25
"""How often a wait wakes up, so Ctrl+C still stops the run."""


class _Call:
    """One call handed to the worker, with its result or error."""

    def __init__(self, work: Callable[[], Any]) -> None:
        self.work = work
        self.done = threading.Event()
        self.result: Any = None
        self.error: BaseException | None = None

    def execute(self) -> None:
        try:
            self.result = self.work()
        except BaseException as exc:  # raised again in the waiting thread
            self.error = exc
        finally:
            self.done.set()


class Watchdog:
    """Run calls on one worker thread and stop waiting for a call after ``timeout`` seconds.

    The worker is a daemon thread, so a call that never ends does not keep the process
    alive. Once a call has hung, every later call fails at once: the device stopped
    answering.
    """

    def __init__(self, timeout: float = COMMAND_TIMEOUT) -> None:
        self.timeout = timeout
        self.hung: str | None = None
        """The call that did not end in time, if any."""
        self._calls: queue.SimpleQueue = queue.SimpleQueue()
        self._worker: threading.Thread | None = None

    def run(self, name: str, work: Callable[[], T]) -> T:
        """Return ``work()``, or raise :class:`DeviceNotRespondingError` after ``timeout``.

        ``name`` names the call in the error, such as the device method.
        """
        if self.hung is not None:
            raise DeviceNotRespondingError(f"MuMu stopped answering earlier ({self.hung})")
        if self._worker is None:
            self._worker = threading.Thread(target=self._serve, name="device", daemon=True)
            self._worker.start()
        call = _Call(work)
        self._calls.put(call)
        left = self.timeout
        while True:
            step = min(_WAKE_SECONDS, left)
            if call.done.wait(step):
                break
            left -= step
            if left <= 0:
                self.hung = name
                raise DeviceNotRespondingError(
                    f"MuMu did not answer {name} within {self.timeout:g} s"
                )
        if call.error is not None:
            raise call.error
        return call.result

    def _serve(self) -> None:
        while True:
            self._calls.get().execute()


class GuardedDevice:
    """Hand every method call on ``device`` to ``watchdog``; other attributes read directly."""

    def __init__(self, device: Any, watchdog: Watchdog) -> None:
        self._device = device
        self._watchdog = watchdog

    def __getattr__(self, name: str) -> Any:
        attribute = getattr(self._device, name)
        if not callable(attribute):
            return attribute

        def call(*args: Any, **kwargs: Any) -> Any:
            return self._watchdog.run(name, lambda: attribute(*args, **kwargs))

        return call
