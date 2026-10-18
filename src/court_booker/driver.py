"""The driver (``android/``) as the device the booking flow drives.

The driver is our own small APK, run in MuMu as an instrumentation (``am instrument``). It
gets Android's UiAutomation, the connection uiautomator2 uses; it is not an accessibility
service, and the app books with it running (field notes, "Instrumentation driver"). It reads
the screen in about 13 ms where uiautomator2 needs 100 ms, and clicks an element by its
label in the tree of the moment, so no position travels from the PC: a list that moved since
the last read cannot send a click to another element.

It speaks protocol 1: one JSON line per command and reply over the abstract socket
``court-driver``, which ``adb forward`` brings to a local TCP port. Only one UiAutomation can
run at a time, so :func:`connect_driver` ends a uiautomator2 server first, and a run stops
the driver when it ends (:meth:`DriverDevice.close`).
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import logging
import socket
import time
from pathlib import Path
from typing import Any, BinaryIO, Callable

from court_booker.adb import LOCALHOST, Adb
from court_booker.errors import DeviceNotRespondingError, DriverError, DriverUnavailableError
from court_booker.geometry import parse_bounds

logger = logging.getLogger(__name__)

PACKAGE = "dev.courtbooker.driver"
INSTRUMENTATION = f"{PACKAGE}/.Driver"
SOCKET = "localabstract:court-driver"
PROTOCOL = 1
APK = Path(__file__).resolve().parent / "assets" / "court-driver.apk"
COMMAND_TIMEOUT = 10.0
"""Seconds the driver may take to answer a command; a read takes about 13 ms."""
START_TIMEOUT = 10.0
"""Seconds the driver may take to answer once started; it took 0.8-2.5 s (2026-10-18)."""
_HELLO_INTERVAL = 0.1
_U2_SERVER = "'com.wetest.uia2.Mai[n]'"
"""The uiautomator2 server process, which holds UiAutomation while it runs. The pattern does
not match the shell running ``pkill``, whose command line holds the pattern itself."""
_LOG = "/data/local/tmp/court-driver.log"
"""What ``am instrument`` prints, such as a crash of the driver."""

Connect = Callable[[int], BinaryIO]
"""Open a stream to the driver behind local ``port``."""


def open_stream(port: int, timeout: float = COMMAND_TIMEOUT) -> BinaryIO:
    """Connect to the driver behind local ``port``; each read may take ``timeout``."""
    sock = socket.create_connection((LOCALHOST, port), timeout=timeout)
    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    stream = sock.makefile("rwb")
    # The stream keeps the socket open; closing the stream closes it.
    sock.close()
    return stream


class DriverClient:
    """Send commands to the driver and return its replies, one JSON line each."""

    def __init__(self, stream: BinaryIO) -> None:
        self._stream = stream
        self._id = 0
        self._broken: str | None = None

    def call(self, op: str, **args: Any) -> dict[str, Any]:
        """Return the driver's reply to ``op``; raise :class:`DriverError` if it refuses."""
        if self._broken is not None:
            raise DriverError(f"The driver connection is lost ({self._broken})")
        self._id += 1
        line = json.dumps({"id": self._id, "op": op, **args}, ensure_ascii=False) + "\n"
        try:
            self._stream.write(line.encode("utf-8"))
            self._stream.flush()
            raw = self._stream.readline()
        except socket.timeout as exc:
            # A late reply would answer the next command: the connection is unusable.
            self._broken = f"{op} timed out"
            raise DeviceNotRespondingError(f"The driver did not answer {op}") from exc
        except OSError as exc:
            self._broken = f"{op}: {exc}"
            raise DriverError(f"The driver connection failed during {op}: {exc}") from exc
        if not raw:
            self._broken = f"closed during {op}"
            raise DriverError(f"The driver closed the connection during {op}")
        try:
            reply = json.loads(raw)
        except ValueError as exc:
            self._broken = f"no JSON after {op}"
            raise DriverError(f"The driver answered {op} with something else than JSON") from exc
        if reply.get("id") != self._id:
            self._broken = f"reply {reply.get('id')} to command {self._id}"
            raise DriverError(f"The driver answered another command than {op}")
        if not reply.get("ok"):
            raise DriverError(f"The driver refused {op}: {reply.get('error')}")
        return reply

    def close(self) -> None:
        self._stream.close()


class DriverDevice:
    """Offer the device calls the booking flow makes, carried out by the driver.

    Screens, clicks, Back and swipes go to the driver; app starts and shell commands go
    through adb, as uiautomator2 does them.
    """

    driver = "instrumentation"

    def __init__(self, client: DriverClient, adb: Adb, serial: str, port: int) -> None:
        self.client = client
        self.adb = adb
        self.serial = serial
        self.port = port

    def dump_hierarchy(self, compressed: bool = False) -> str:
        """Return the active window in the XML of a uiautomator2 dump."""
        return self.client.call("dump")["xml"]

    def click(self, x: float, y: float, label: str = "") -> None:
        """Click the element labelled ``label`` where it is now.

        ``(x, y)``, where the last read showed it, only picks among elements with the same
        label. An element no longer on the screen is not clicked: whatever is at its old
        place now is another element; the flow reads the screen next and clicks again if it
        has to. An element without a label, such as the consent checkbox, is the smallest
        clickable element at ``(x, y)`` in the tree of the moment.
        """
        point = {"x": round(x), "y": round(y)}
        if label:
            reply = self.client.call("click", label=label, **point)
        else:
            reply = self.client.call("click_at", **point)
        if not reply["clicked"]:
            logger.debug("%s; nothing clicked", f"{label!r} is gone" if label else "No element")
            return
        box = parse_bounds(reply.get("bounds", ""))
        if box is not None and not (box[0] <= x <= box[2] and box[1] <= y <= box[3]):
            logger.debug("%r had moved to %s; clicked it there", label, reply["bounds"])
        if reply.get("how") != "action":
            logger.debug("%r clicked with a touch", label)

    def press(self, key: str) -> None:
        if key != "back":
            raise ValueError(f"The driver cannot press {key!r}")
        self.client.call("back")

    def swipe(self, x1: float, y1: float, x2: float, y2: float, duration: float = 0.1) -> None:
        """Swipe from ``(x1, y1)`` to ``(x2, y2)`` in ``duration`` seconds."""
        self.client.call(
            "swipe",
            x1=round(x1),
            y1=round(y1),
            x2=round(x2),
            y2=round(y2),
            ms=round(duration * 1000),
        )

    def shell(self, command: str) -> str:
        return self.adb.shell(self.serial, command)

    def app_start(self, package: str) -> None:
        """Open ``package`` at its launcher activity, as uiautomator2 does."""
        self.shell(f"monkey -p {package} -c android.intent.category.LAUNCHER 1")

    def app_stop(self, package: str) -> None:
        self.shell(f"am force-stop {package}")

    def app_current(self) -> dict[str, str]:
        """Return ``{"package": ...}`` for the active window, like uiautomator2."""
        return {"package": self.client.call("current")["package"]}

    def close(self) -> None:
        """Stop the driver, so uiautomator2 and other tools can use UiAutomation again."""
        stop_driver(self.adb, self.serial, self.client, self.port)


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ensure_installed(adb: Adb, serial: str, apk: Path = APK) -> None:
    """Install the driver ``apk`` unless the emulator holds the same file already.

    Android keeps an installed APK as it was sent, so equal hashes mean the same driver. One
    signed with another key cannot be updated in place: it is removed first.
    """
    if not apk.is_file():
        raise DriverUnavailableError(f"The driver APK is missing ({apk})")
    installed = adb.shell(serial, "pm", "path", PACKAGE).strip()
    if installed.startswith("package:"):
        path = installed.splitlines()[0][len("package:") :]
        if adb.shell(serial, "sha256sum", path).split(" ")[0] == file_hash(apk):
            return
    logger.info("Installing the driver")
    output = adb.install(serial, apk)
    if "INSTALL_FAILED_UPDATE_INCOMPATIBLE" in output:
        adb.shell(serial, "pm", "uninstall", PACKAGE)
        output = adb.install(serial, apk)
    if "Success" not in output:
        raise DriverUnavailableError(f"The driver could not be installed: {output.strip()}")


def start_driver(adb: Adb, serial: str) -> None:
    """End a uiautomator2 server, which holds UiAutomation, and start the driver.

    ``am instrument`` must outlive this adb shell, since it holds the UiAutomation
    connection: it runs detached (``setsid nohup``).
    """
    logger.info("Starting the driver")
    adb.shell(
        serial,
        f"pkill -f {_U2_SERVER}; setsid nohup am instrument -w {INSTRUMENTATION} "
        f"> {_LOG} 2>&1 < /dev/null &",
    )


def stop_driver(adb: Adb, serial: str, client: DriverClient | None, port: int | None) -> None:
    """Ask the driver to stop, end it if it does not, and drop the forward."""
    if client is not None:
        # A driver that does not answer is ended below in any case.
        with contextlib.suppress(DriverError, DeviceNotRespondingError):
            client.call("stop")
        client.close()
    adb.shell(serial, "am", "force-stop", PACKAGE)
    if port is not None:
        adb.forward_remove(serial, port)


def hello(connect: Connect, port: int) -> DriverClient | None:
    """Return a client if the driver answers ``hello`` on ``port``, else ``None``.

    A forward with no driver behind it accepts the connection and closes it at once.
    """
    try:
        stream = connect(port)
    except OSError:
        return None
    client = DriverClient(stream)
    try:
        reply = client.call("hello")
    except (DriverError, DeviceNotRespondingError):
        client.close()
        return None
    if reply.get("protocol") != PROTOCOL:
        client.close()
        raise DriverUnavailableError(
            f"The driver {reply.get('version')} speaks protocol {reply.get('protocol')}, "
            f"not {PROTOCOL}"
        )
    logger.info("Driver %s answers (protocol %d)", reply.get("version"), PROTOCOL)
    return client


def connect_driver(
    adb: Adb,
    serial: str,
    connect: Connect = open_stream,
    clock: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
    apk: Path = APK,
) -> DriverDevice:
    """Return the driver on ``serial`` as a device, installing and starting it if needed.

    Raises :class:`DriverUnavailableError` when it cannot be installed or does not answer;
    the driver is then stopped, so uiautomator2 can take over.
    """
    ensure_installed(adb, serial, apk)
    port = adb.forward(serial, SOCKET)
    client = hello(connect, port)
    if client is None:
        start_driver(adb, serial)
        deadline = clock() + START_TIMEOUT
        while client is None:
            if clock() >= deadline:
                stop_driver(adb, serial, None, port)
                raise DriverUnavailableError(
                    f"The driver did not answer {START_TIMEOUT:.0f} s after being started"
                )
            sleep(_HELLO_INTERVAL)
            client = hello(connect, port)
    return DriverDevice(client, adb, serial, port)
