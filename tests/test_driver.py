"""The driver's client, device, install and start-up, with its socket and adb replaced."""

import hashlib
import json
import logging
import socket

import pytest

from court_booker import driver
from court_booker.driver import DriverClient, DriverDevice, connect_driver, ensure_installed
from court_booker.errors import DeviceNotRespondingError, DriverError, DriverUnavailableError

SERIAL = "127.0.0.1:16384"
APK_PATH = "/data/app/~~x/dev.courtbooker.driver-y/base.apk"


class FakeStream:
    """Stand in for the driver's socket: answer each JSON line with ``reply(command)``.

    ``reply`` returns the reply's fields (``ok`` and ``id`` are added), raw bytes, or an
    exception the read raises.
    """

    def __init__(self, reply=lambda command: {}):
        self.reply = reply
        self.commands = []
        self.closed = False
        self._answer = b""

    def write(self, data):
        command = json.loads(data)
        self.commands.append(command)
        answer = self.reply(command)
        if isinstance(answer, (bytes, BaseException)):
            self._answer = answer
        else:
            reply = {"id": command["id"], "ok": True, **answer}
            self._answer = (json.dumps(reply) + "\n").encode()

    def flush(self):
        pass

    def readline(self):
        if isinstance(self._answer, BaseException):
            raise self._answer
        return self._answer

    def close(self):
        self.closed = True


def driver_stream(**replies):
    """Return a stream that answers like a running driver; ``replies`` overrides ops."""
    defaults = {
        "hello": {"protocol": 1, "version": "c52e8ff35726"},
        "click": {"clicked": True, "how": "action"},
        "click_at": {"clicked": True, "how": "action"},
    }
    defaults.update(replies)
    return FakeStream(lambda command: defaults.get(command["op"], {}))


CLOSED = FakeStream(lambda command: b"")
"""A forward with no driver behind it: the connection closes at once."""


class FakeAdb:
    def __init__(self, installed_hash=None, installs=("Success\n",)):
        self.installed_hash = installed_hash
        self.installs = list(installs)
        self.shells = []
        self.installed = []
        self.removed = []

    def forward(self, serial, remote):
        assert remote == "localabstract:court-driver"
        return 27183

    def forward_remove(self, serial, port):
        self.removed.append(port)

    def install(self, serial, apk):
        self.installed.append(apk)
        return self.installs.pop(0)

    def shell(self, serial, *args):
        command = " ".join(args)
        self.shells.append(command)
        if command == f"pm path {driver.PACKAGE}":
            return "" if self.installed_hash is None else f"package:{APK_PATH}\n"
        if command == f"sha256sum {APK_PATH}":
            return f"{self.installed_hash}  {APK_PATH}\n"
        return ""


@pytest.fixture
def apk(tmp_path):
    path = tmp_path / "court-driver.apk"
    path.write_bytes(b"driver apk")
    return path


def apk_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def device(stream, adb=None):
    return DriverDevice(DriverClient(stream), adb or FakeAdb(), SERIAL, 27183)


# Client ---------------------------------------------------------------------


def test_each_command_is_one_json_line_with_its_own_id():
    stream = driver_stream()
    client = DriverClient(stream)

    assert client.call("hello")["protocol"] == 1
    client.call("click_at", x=43, y=1345)

    assert stream.commands == [
        {"id": 1, "op": "hello"},
        {"id": 2, "op": "click_at", "x": 43, "y": 1345},
    ]


def test_a_refused_command_raises_with_the_drivers_message():
    client = DriverClient(FakeStream(lambda c: {"ok": False, "error": "No value for y"}))

    with pytest.raises(DriverError, match="refused click_at: No value for y"):
        client.call("click_at", x=1)


def test_a_closed_connection_fails_this_and_every_later_command():
    client = DriverClient(FakeStream(lambda command: b""))

    with pytest.raises(DriverError, match="closed the connection during dump"):
        client.call("dump")
    with pytest.raises(DriverError, match="connection is lost"):
        client.call("dump")


def test_a_driver_that_does_not_answer_counts_as_a_frozen_device():
    client = DriverClient(FakeStream(lambda command: socket.timeout("timed out")))

    with pytest.raises(DeviceNotRespondingError, match="did not answer dump"):
        client.call("dump")
    with pytest.raises(DriverError, match="dump timed out"):
        client.call("back")


def test_a_reply_to_another_command_breaks_the_connection():
    client = DriverClient(FakeStream(lambda command: b'{"id": 7, "ok": true}\n'))

    with pytest.raises(DriverError, match="another command"):
        client.call("back")
    with pytest.raises(DriverError, match="connection is lost"):
        client.call("back")


def test_a_reply_that_is_not_json_breaks_the_connection():
    client = DriverClient(FakeStream(lambda command: b"garbage\n"))

    with pytest.raises(DriverError, match="else than JSON"):
        client.call("back")


# Device ---------------------------------------------------------------------


def test_a_tap_with_a_label_clicks_that_element():
    stream = driver_stream(click={"clicked": True, "how": "action", "bounds": "[35,925][505,1045]"})

    device(stream).click(270, 985, label="S6 - Sân tennis")

    assert stream.commands == [
        {"id": 1, "op": "click", "label": "S6 - Sân tennis", "x": 270, "y": 985}
    ]


def test_a_label_that_moved_is_clicked_where_it_is_and_logged(caplog):
    stream = driver_stream(click={"clicked": True, "how": "action", "bounds": "[35,925][505,1045]"})

    with caplog.at_level(logging.DEBUG, logger="court_booker.driver"):
        device(stream).click(270, 1217, label="S6 - Sân tennis")

    assert [c["op"] for c in stream.commands] == ["click"]
    assert "'S6 - Sân tennis' had moved to [35,925][505,1045]" in caplog.text


def test_a_label_no_longer_shown_is_not_clicked_at_its_old_place(caplog):
    # The venue screen gave way to the court list: its old place holds S10 now.
    stream = driver_stream(click={"clicked": False})

    with caplog.at_level(logging.DEBUG, logger="court_booker.driver"):
        device(stream).click(270.4, 1079.6, label="Origami_ Sân tennis")

    assert stream.commands == [
        {"id": 1, "op": "click", "label": "Origami_ Sân tennis", "x": 270, "y": 1080}
    ]
    assert "'Origami_ Sân tennis' is gone; nothing clicked" in caplog.text


def test_an_element_that_takes_no_click_is_touched_and_logged(caplog):
    stream = driver_stream(click={"clicked": True, "how": "touch", "bounds": "[0,0][10,10]"})

    with caplog.at_level(logging.DEBUG, logger="court_booker.driver"):
        device(stream).click(5, 5, label="Thông tin dịch vụ")

    assert "'Thông tin dịch vụ' clicked with a touch" in caplog.text


def test_a_tap_without_a_label_clicks_the_element_at_that_point():
    stream = driver_stream()

    device(stream).click(57, 1345)

    assert stream.commands == [{"id": 1, "op": "click_at", "x": 57, "y": 1345}]


def test_back_is_the_only_key():
    stream = driver_stream()
    driver_device = device(stream)

    driver_device.press("back")
    with pytest.raises(ValueError):
        driver_device.press("home")

    assert stream.commands == [{"id": 1, "op": "back"}]


def test_a_swipe_takes_its_duration_in_milliseconds():
    stream = driver_stream()

    device(stream).swipe(270.0, 992.0, 270.0, 608.0, 0.25)

    assert stream.commands == [
        {"id": 1, "op": "swipe", "x1": 270, "y1": 992, "x2": 270, "y2": 608, "ms": 250}
    ]


def test_screens_and_the_current_app_come_from_the_driver():
    stream = driver_stream(dump={"xml": "<hierarchy/>"}, current={"package": "a.b"})
    driver_device = device(stream)

    assert driver_device.dump_hierarchy(compressed=False) == "<hierarchy/>"
    assert driver_device.app_current() == {"package": "a.b"}
    assert driver_device.driver == "instrumentation"


def test_the_app_is_started_and_stopped_through_adb():
    adb = FakeAdb()
    driver_device = device(driver_stream(), adb)

    driver_device.app_stop("com.vinhomes.resident")
    driver_device.app_start("com.vinhomes.resident")

    assert adb.shells == [
        "am force-stop com.vinhomes.resident",
        "monkey -p com.vinhomes.resident -c android.intent.category.LAUNCHER 1",
    ]


def test_closing_stops_the_driver_and_drops_the_forward():
    adb = FakeAdb()
    stream = driver_stream()

    device(stream, adb).close()

    assert stream.commands == [{"id": 1, "op": "stop"}]
    assert stream.closed
    # Ended by Android too, in case it did not stop by itself.
    assert adb.shells == [f"am force-stop {driver.PACKAGE}"]
    assert adb.removed == [27183]


def test_closing_a_driver_that_does_not_answer_still_ends_it():
    adb = FakeAdb()

    device(FakeStream(lambda command: socket.timeout("timed out")), adb).close()

    assert adb.shells == [f"am force-stop {driver.PACKAGE}"]
    assert adb.removed == [27183]


# Install --------------------------------------------------------------------


def test_the_same_driver_is_not_installed_again(apk):
    adb = FakeAdb(installed_hash=apk_hash(apk))

    ensure_installed(adb, SERIAL, apk)

    assert adb.installed == []


def test_a_missing_driver_is_installed(apk):
    adb = FakeAdb()

    ensure_installed(adb, SERIAL, apk)

    assert adb.installed == [apk]


def test_another_driver_is_replaced(apk):
    adb = FakeAdb(installed_hash="0" * 64)

    ensure_installed(adb, SERIAL, apk)

    assert adb.installed == [apk]


def test_a_driver_signed_with_another_key_is_removed_first(apk):
    adb = FakeAdb(
        installed_hash="0" * 64,
        installs=["Failure [INSTALL_FAILED_UPDATE_INCOMPATIBLE: ...]\n", "Success\n"],
    )

    ensure_installed(adb, SERIAL, apk)

    assert adb.installed == [apk, apk]
    assert f"pm uninstall {driver.PACKAGE}" in adb.shells


def test_a_failed_install_makes_the_driver_unavailable(apk):
    adb = FakeAdb(installs=["Failure [INSTALL_FAILED_INSUFFICIENT_STORAGE]\n"])

    with pytest.raises(DriverUnavailableError, match="INSUFFICIENT_STORAGE"):
        ensure_installed(adb, SERIAL, apk)


def test_a_missing_apk_makes_the_driver_unavailable(tmp_path):
    with pytest.raises(DriverUnavailableError, match="APK is missing"):
        ensure_installed(FakeAdb(), SERIAL, tmp_path / "none.apk")


def test_the_package_ships_the_driver():
    assert driver.APK.is_file()


# Start-up -------------------------------------------------------------------


class FakeTime:
    def __init__(self):
        self.now = 0.0

    def clock(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds


def connect(adb, streams, apk, time=None):
    time = time or FakeTime()
    queue = list(streams)
    return connect_driver(
        adb,
        SERIAL,
        connect=lambda port: queue.pop(0) if len(queue) > 1 else queue[0],
        clock=time.clock,
        sleep=time.sleep,
        apk=apk,
    )


def test_a_running_driver_is_used_as_it_is(apk):
    adb = FakeAdb(installed_hash=apk_hash(apk))

    result = connect(adb, [driver_stream()], apk)

    assert result.driver == "instrumentation"
    assert result.port == 27183
    assert adb.shells == [f"pm path {driver.PACKAGE}", f"sha256sum {APK_PATH}"]


def test_a_driver_that_does_not_answer_is_started(apk):
    adb = FakeAdb(installed_hash=apk_hash(apk))

    result = connect(adb, [CLOSED, CLOSED, CLOSED, driver_stream()], apk)

    assert result.driver == "instrumentation"
    # uiautomator2 holds UiAutomation while it runs; am instrument must outlive adb shell.
    assert adb.shells[2] == (
        "pkill -f 'com.wetest.uia2.Mai[n]'; setsid nohup am instrument -w "
        f"{driver.INSTRUMENTATION} > /data/local/tmp/court-driver.log 2>&1 < /dev/null &"
    )


def test_a_driver_that_never_answers_is_stopped_and_unavailable(apk):
    adb = FakeAdb(installed_hash=apk_hash(apk))
    time = FakeTime()

    with pytest.raises(DriverUnavailableError, match="did not answer 10 s after being started"):
        connect(adb, [CLOSED], apk, time)

    assert time.now >= driver.START_TIMEOUT
    # So uiautomator2 can take over.
    assert adb.shells[-1] == f"am force-stop {driver.PACKAGE}"
    assert adb.removed == [27183]


def test_a_refused_connection_counts_as_no_answer():
    def refuse(port):
        raise ConnectionRefusedError("refused")

    assert driver.hello(refuse, 27183) is None


def test_a_driver_of_another_protocol_is_unavailable(apk):
    stream = driver_stream(hello={"protocol": 2, "version": "abc"})

    with pytest.raises(DriverUnavailableError, match=r"abc speaks protocol 2, not 1"):
        connect(FakeAdb(installed_hash=apk_hash(apk)), [stream], apk)

    assert stream.closed
