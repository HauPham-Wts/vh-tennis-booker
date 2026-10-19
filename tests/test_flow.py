"""Flow tests against a scripted fake app; no emulator required."""

import logging
import threading
from datetime import date
from xml.sax.saxutils import quoteattr

import pytest

import court_booker.flow as flow
from court_booker.config import Config
from court_booker.errors import (
    AppNotReadyError,
    BookingNotOpenError,
    BookingRejectedError,
    BookingUnconfirmedError,
    DeviceNotRespondingError,
    ElementNotFoundError,
    NavigationError,
    SlotUnavailableError,
)
from court_booker.events import EventKind, MemorySink, Reporter
from court_booker.flow import Booked, Booker
from court_booker.screen import Node, Screen
from court_booker.watchdog import GuardedDevice, Watchdog

WIDTH, HEIGHT = 540, 1600
TARGET = date(2026, 10, 11)
DAY_10 = "10, Thứ Bảy, 10 tháng 10, 2026"
DAY_11 = "11, Chủ Nhật, 11 tháng 10, 2026"
CHECKBOX = (35, 1323, 79, 1367)


def node(desc, box, clickable=True):
    return desc, box, clickable


CONTINUE = node("Tiếp tục", (35, 1490, 505, 1584))
DAYS = [node(DAY_10, (381, 344, 455, 402)), node(DAY_11, (455, 344, 529, 402))]
SLOTS = [
    node("11:00 - 12:00", (277, 884, 502, 968)),
    node("14:00 - 15:00\nHết chỗ", (38, 982, 263, 1066)),
]
COURTS = [
    node("S10 - Sân tennis", (35, 1024, 505, 1144)),
    node("S9 - Sân tennis\nHết chỗ", (35, 1157, 505, 1277)),
]
QUOTA_MESSAGE = "Căn hộ đã hết hạn mức đăng ký tiện ích cho phép."
NOTICE = [  # read from the device on 2026-10-10; the dialog hides the page beneath
    node("", (0, 0, 540, 1600)),
    node("Thông báo", (0, 33, 540, 1600), False),
    node(QUOTA_MESSAGE, (47, 758, 493, 817), False),
    node("Đóng", (47, 841, 493, 936)),
    node("7:43 PM", (6, 5, 50, 28), False),
    node("Wifi signal full.", (439, 5, 460, 26), False),
]
CONFIRM_PAGE = [
    node("Xác nhận đăng ký", (145, 52, 395, 89), False),
    node("", (0, 1292, 540, 1465)),
    node("", CHECKBOX),
    node("Tôi đã hiểu và đồng ý với ", (79, 1322, 313, 1355), False),
]
TICKET = [node("Chi tiết đặt lịch", (99, 52, 311, 89), False)]  # first read, 2026-10-14
PROCESSING = node("Đang xử lý", (407, 154, 499, 177), False)  # status at 06:00 on 2026-10-15
LOADING = [  # read while the next screen is built, 2026-10-15: only the status bar is labelled
    node("", (0, 0, 540, 1600)),
    node("4:44 PM", (6, 5, 50, 28), False),
    node("Wifi signal full.", (439, 5, 460, 26), False),
]


def details(when="11/10/2026 11:00 - 12:00", court="S10 - Sân tennis"):
    """Return the booking details of the confirmation page: one label, as read on 2026-10-15."""
    return node(
        f"Sân Tennis\nThời gian đặt lịch\n{when}\nVị trí/dịch vụ\n{court}\n"
        "Thông tin thanh toán\nNhà cung cấp\nVinhomes\nTổng tiền\n0 VND",
        (0, 210, 540, 775),
        False,
    )


DETAILS = details()


class FakeApp:
    """Scripted app: each screen is a list of nodes; taps and Back switch screens.

    A switch takes effect at once, like a tap the app handles before the next
    one, or after ``delay`` dumps, like a screen that is still loading. A list of
    switches is followed in turn, each ``delay`` counted from the one before.
    """

    def __init__(self, screens, taps_to, backs_to, screen, launches_to=None, current=""):
        self.screens = screens
        self.taps_to = taps_to
        self.backs_to = backs_to
        self.screen = screen
        self.launches_to = launches_to
        self.current = current
        self.pending = []
        self.swallow = {}
        self.on_swipe = None
        self.ops = []
        self.taps = []
        self.labels = []
        """The label sent with each tap, as the driver needs it."""
        self.calls = []
        self.swipes = 0
        self.swipe_args = []
        self.shells = []

    def go(self, target):
        steps = target if isinstance(target, list) else [target]
        self.pending = [[step, 0] if isinstance(step, str) else list(step) for step in steps]
        self.switch()

    def switch(self):
        while self.pending and self.pending[0][1] <= 0:
            self.screen = self.pending.pop(0)[0]

    def dump_hierarchy(self, compressed=False):
        self.ops.append("dump")
        if self.pending:
            self.pending[0][1] -= 1
            self.switch()
        children = "".join(
            f"<node content-desc={quoteattr(desc, {chr(10): '&#10;'})} "
            f'bounds="[{box[0]},{box[1]}][{box[2]},{box[3]}]" '
            f'clickable="{"true" if clickable else "false"}" />'
            for desc, box, clickable in self.screens[self.screen]
        )
        root = f'<node content-desc="" bounds="[0,0][{WIDTH},{HEIGHT}]" clickable="false">'
        return f"<hierarchy>{root}{children}</node></hierarchy>"

    def click(self, x, y, label=""):
        self.labels.append(label)
        hits = [
            (desc, box)
            for desc, box, _ in self.screens[self.screen]
            if box[0] <= x <= box[2] and box[1] <= y <= box[3]
        ]
        if not hits:
            self.ops.append(("click", None))
            return
        desc, box = min(hits, key=lambda hit: (hit[1][2] - hit[1][0]) * (hit[1][3] - hit[1][1]))
        key = desc or box
        self.ops.append(("click", key))
        self.taps.append(key)
        if self.swallow.get(key, 0) > 0:
            self.swallow[key] -= 1
            return
        target = self.taps_to.get((self.screen, key))
        if target is not None:
            self.go(target)

    def press(self, key):
        self.calls.append(key)
        target = self.backs_to.get(self.screen)
        if target is not None:
            self.go(target)

    def window_size(self):
        # MuMu's tablet resolution reports the landscape size while the app is portrait.
        return HEIGHT, WIDTH

    def swipe(self, *args):
        self.swipes += 1
        self.swipe_args.append(args)
        if self.on_swipe is not None:
            self.on_swipe(self)

    def app_stop(self, package):
        self.calls.append("app_stop")

    def app_start(self, package):
        self.calls.append("app_start")
        if self.launches_to is not None:
            self.go(self.launches_to)

    def app_current(self):
        return {"package": self.current}

    def shell(self, command):
        self.shells.append(command)


def booking_app(
    screen="utilities",
    courts=COURTS,
    via_venue=False,
    slot_delay=0,
    shown=(DETAILS,),
    ticket=TICKET,
):
    screens = {
        "loading": LOADING,
        "home": [node("Tiện ích", (200, 1500, 340, 1580))],
        "utilities": [node("Sân Tennis", (35, 300, 505, 360))],
        "calendar": [*DAYS, CONTINUE],
        "calendar_slots": DAYS + SLOTS + [CONTINUE],
        "calendar_selected": DAYS + SLOTS + [CONTINUE],
        "venue": [node("Origami Grand Park", (35, 600, 505, 700))],
        "courts": courts,
        "details": [node("S10 - Sân tennis", (116, 975, 274, 1004), False), CONTINUE],
        "confirm": [*CONFIRM_PAGE, *shown, node("Xác nhận", (35, 1490, 505, 1584), False)],
        "confirm_ticked": [*CONFIRM_PAGE, *shown, node("Xác nhận", (35, 1490, 505, 1584))],
        "ticket": ticket,
    }
    taps_to = {
        ("home", "Tiện ích"): "utilities",
        ("utilities", "Sân Tennis"): "calendar",
        ("calendar", DAY_11): ("calendar_slots", slot_delay),
        ("calendar_slots", "11:00 - 12:00"): "calendar_selected",
        ("calendar_selected", "Tiếp tục"): "venue" if via_venue else "courts",
        ("venue", "Origami Grand Park"): "courts",
        ("courts", "S10 - Sân tennis"): "details",
        ("details", "Tiếp tục"): "confirm",
        ("confirm", CHECKBOX): "confirm_ticked",
        ("confirm_ticked", "Xác nhận"): "ticket",
    }
    backs_to = {
        "utilities": "home",
        "ticket": "utilities",
        "confirm": "details",
        "confirm_ticked": "details",
        "details": "courts",
        "courts": "venue" if via_venue else "calendar_selected",
        "venue": "calendar_selected",
        "calendar": "utilities",
        "calendar_slots": "utilities",
        "calendar_selected": "utilities",
    }
    return FakeApp(screens, taps_to, backs_to, screen, launches_to="home")


@pytest.fixture(autouse=True)
def fake_time(monkeypatch):
    """Make sleeps advance a fake monotonic clock, so timeouts pass instantly."""
    now = [0.0]
    monkeypatch.setattr(flow.time, "monotonic", lambda: now[0])
    monkeypatch.setattr(flow.time, "sleep", lambda seconds: now.__setitem__(0, now[0] + seconds))
    return now


FULL_ROUND = [
    "Sân Tennis",
    DAY_11,
    "11:00 - 12:00",
    "Tiếp tục",
    "S10 - Sân tennis",
    "Tiếp tục",
    CHECKBOX,
    "Xác nhận",
]


def test_book_reads_each_screen_once_and_taps_by_coordinates():
    app = booking_app()
    booker = Booker(app, Config())

    booker.book("11:00 - 12:00", TARGET)

    assert app.taps == FULL_ROUND
    assert app.screen == "ticket"
    # 8 taps plus one read per screen: start, calendar, slots, courts, details,
    # confirmation, enabled confirm button, ticket.
    assert booker.commands == 16


def test_every_tap_names_its_element_for_the_driver():
    app = booking_app()

    Booker(app, Config()).book("11:00 - 12:00", TARGET)

    # The driver clicks by label; the consent checkbox has none and goes by position.
    assert app.labels == [tap if isinstance(tap, str) else "" for tap in FULL_ROUND]


def test_continue_waits_for_the_app_to_take_the_slot(fake_time):
    app = booking_app()
    tapped = {}
    click = app.click

    def timed_click(x, y, label=""):
        tapped.setdefault(label, fake_time[0])
        click(x, y, label)

    app.click = timed_click
    Booker(app, Config()).book("11:00 - 12:00", TARGET)

    # Sooner, the app books the slot selected before (field notes).
    assert tapped["Tiếp tục"] - tapped["11:00 - 12:00"] >= flow._SLOT_SETTLE


def test_confirm_waits_for_the_app_to_take_the_tick(fake_time):
    app = booking_app()
    tapped = {}
    click = app.click

    def timed_click(x, y, label=""):
        tapped[label] = fake_time[0]
        click(x, y, label)

    app.click = timed_click
    booker = Booker(app, Config())
    booker.book("11:00 - 12:00", TARGET)

    # Sooner, the app ignores "Xác nhận" (field notes); the checkbox has no label.
    assert tapped["Xác nhận"] - tapped[""] >= flow._TERMS_SETTLE
    assert booker.commands == 16


def test_book_reports_each_step_without_extra_commands():
    app = booking_app()
    sink = MemorySink()
    booker = Booker(app, Config(), Reporter(sink))

    booker.book("11:00 - 12:00", TARGET)

    assert sink.kinds == [
        EventKind.CALENDAR_OPENED,
        EventKind.DATE_SELECTED,
        EventKind.SLOT_SELECTED,
        EventKind.COURT_SELECTED,
        EventKind.TERMS_ACCEPTED,
    ]
    assert [event.data for event in sink.events] == [
        {"attempt": 1},
        {"date": "2026-10-11"},
        {"slot": "11:00 - 12:00", "swipes": 0},
        {"court": "S10 - Sân tennis"},
        {},
    ]
    assert booker.commands == 16


def test_every_new_screen_is_logged_once(caplog):
    caplog.set_level(logging.DEBUG, logger="court_booker")
    app = booking_app(slot_delay=5)  # the calendar is read six times before slots show
    booker = Booker(app, Config())

    booker.book("11:00 - 12:00", TARGET)

    screens = [r.getMessage() for r in caplog.records if r.getMessage().startswith("Screen (")]
    # utilities, calendar, slots, courts, details, confirmation before and after the tick,
    # ticket; the slot list after the slot tap reads the same and is not logged again.
    assert len(screens) == len(set(screens)) == 8
    assert screens[0].startswith("Screen (1 elements):\n  [35,300][505,360] clickable 'Sân")
    assert screens[-1] == "Screen (1 elements):\n  [99,52][311,89] 'Chi tiết đặt lịch'"
    assert booker.commands == app.ops.count("dump") + len(app.taps)


def test_taps_and_back_presses_are_logged(caplog):
    caplog.set_level(logging.DEBUG, logger="court_booker")
    app = booking_app()
    booker = Booker(app, Config())

    booker.book("11:00 - 12:00", TARGET)
    booker.return_to_utilities()

    messages = [record.getMessage() for record in caplog.records]
    assert "Tap 'Sân Tennis' at (270, 330)" in messages
    assert "Tap (57, 1345)" in messages  # the unlabelled consent checkbox
    assert messages[-2:] == [
        "Press Back",
        "Screen (1 elements):\n  [35,300][505,360] clickable 'Sân Tennis'",
    ]


def test_book_waits_for_slow_slot_list():
    app = booking_app(slot_delay=5)

    Booker(app, Config()).book("11:00 - 12:00", TARGET)

    assert app.taps == FULL_ROUND


def test_dry_run_stops_before_final_confirmation():
    app = booking_app()

    booked = Booker(app, Config()).book("11:00 - 12:00", TARGET, dry_run=True)

    assert app.taps == FULL_ROUND[:-1]
    assert app.screen == "confirm_ticked"
    assert booked.event_data() == {
        "shown_date": "2026-10-11",
        "shown_slot": "11:00 - 12:00",
        "shown_court": "S10 - Sân tennis",
    }


def test_book_returns_what_the_confirmation_page_and_ticket_showed(caplog):
    caplog.set_level(logging.INFO, logger="court_booker")
    app = booking_app(ticket=[*TICKET, PROCESSING])
    booker = Booker(app, Config())

    booked = booker.book("11:00 - 12:00", TARGET)

    assert booked == Booked("2026-10-11", "11:00 - 12:00", "S10 - Sân tennis", "Đang xử lý")
    assert "Confirmation page: 2026-10-11 11:00 - 12:00 on S10 - Sân tennis" in caplog.text
    assert booker.commands == 16


def test_other_court_on_the_confirmation_page_is_booked_with_a_warning(caplog):
    app = booking_app(shown=[details(court="S9 - Sân tennis")])

    booked = Booker(app, Config()).book("11:00 - 12:00", TARGET)

    assert app.taps == FULL_ROUND
    assert booked.shown_court == "S9 - Sân tennis"
    [warning] = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert warning.getMessage() == (
        "The confirmation page books 2026-10-11 11:00 - 12:00 on S9 - Sân tennis, "
        "not 2026-10-11 11:00 - 12:00 on S10 - Sân tennis; confirming anyway"
    )


def test_confirmation_page_without_details_only_warns(caplog):
    app = booking_app(shown=[])

    booked = Booker(app, Config()).book("11:00 - 12:00", TARGET)

    assert app.screen == "ticket"
    assert booked == Booked()
    assert "Could not read the date, slot and court on the confirmation page" in caplog.text


def test_frames_without_the_ticket_are_read_again_until_it_shows():
    app = booking_app()
    # 2026-10-15: the page stays while the server answers, then a frame without labels.
    app.taps_to[("confirm_ticked", "Xác nhận")] = [("loading", 2), ("ticket", 2)]
    booker = Booker(app, Config())

    booked = booker.book("11:00 - 12:00", TARGET)

    assert app.screen == "ticket"
    assert booked.ticket_status is None
    assert booker.commands == 16 + 3  # the page and the empty frame were read too


def test_notice_after_a_frame_without_labels_fails_the_round():
    app = refusing_app()
    app.taps_to[("confirm_ticked", "Xác nhận")] = ["loading", ("notice", 2)]

    with pytest.raises(BookingRejectedError, match=f"refused the booking: {QUOTA_MESSAGE}"):
        Booker(app, Config()).book("11:00 - 12:00", TARGET)


@pytest.mark.parametrize("after", ["loading", "confirm_ticked"])
def test_neither_ticket_nor_notice_in_time_fails_the_round_as_unknown(after, fake_time):
    app = booking_app()
    app.taps_to[("confirm_ticked", "Xác nhận")] = after

    with pytest.raises(BookingUnconfirmedError, match=r"Outcome unknown: .* 10 s after confirming"):
        Booker(app, Config()).book("11:00 - 12:00", TARGET)

    assert app.taps == FULL_ROUND  # "Xác nhận" is never tapped again
    assert fake_time[0] >= 10


def test_book_taps_venue_screen_when_shown():
    app = booking_app(via_venue=True)

    Booker(app, Config()).book("11:00 - 12:00", TARGET)

    assert app.taps[4] == "Origami Grand Park"
    assert app.screen == "ticket"


def refusing_app(**options):
    """Answer "Xác nhận" with a notice dialog, as when someone else took the slot first."""
    app = booking_app(**options)
    app.screens["notice"] = NOTICE
    app.taps_to[("confirm_ticked", "Xác nhận")] = "notice"
    app.backs_to["notice"] = "confirm_ticked"
    return app


def test_notice_after_confirming_fails_the_round_with_its_message():
    app = refusing_app()
    booker = Booker(app, Config())

    with pytest.raises(BookingRejectedError, match=f"refused the booking: {QUOTA_MESSAGE}"):
        booker.book("11:00 - 12:00", TARGET)

    assert app.taps == FULL_ROUND
    assert booker.commands == 16


def test_fully_booked_court_fails_the_round():
    app = booking_app(courts=[node("S10 - Sân tennis\nHết chỗ", (35, 1024, 505, 1144))])

    with pytest.raises(SlotUnavailableError, match="Court S10"):
        Booker(app, Config()).book("11:00 - 12:00", TARGET)


def test_fully_booked_slot_fails_the_round():
    app = booking_app()

    with pytest.raises(SlotUnavailableError, match="14:00 - 15:00 is fully booked"):
        Booker(app, Config()).book("14:00 - 15:00", TARGET)


def test_swallowed_tap_is_retried():
    app = booking_app()
    app.swallow = {"Sân Tennis": 1}

    Booker(app, Config()).book("11:00 - 12:00", TARGET)

    assert app.taps.count("Sân Tennis") == 2
    assert app.screen == "ticket"


COURTS_MOVED = [  # the court list once the service info above it has loaded, 232 px higher
    node("S10 - Sân tennis", (35, 792, 505, 912)),
    node("S9 - Sân tennis\nHết chỗ", (35, 925, 505, 1045)),
]
OTHER_DETAILS = [node("S8 - Sân tennis", (116, 975, 274, 1004), False), CONTINUE]


def moving_courts_app(first_tap):
    """Move the court list under the first court tap, which leads to ``first_tap``.

    That is the details page of the court two places lower if it is free, as on 2026-10-17
    (S6 tapped, S9 opened), or the moved list if it is full and the tap did nothing.
    """
    app = booking_app()
    app.screens["courts_moved"] = COURTS_MOVED
    app.screens["details_other"] = OTHER_DETAILS
    app.taps_to[("courts", "S10 - Sân tennis")] = first_tap
    app.taps_to[("courts_moved", "S10 - Sân tennis")] = "details"
    app.backs_to["details_other"] = "courts_moved"
    return app


def test_another_court_opened_is_left_and_the_court_tapped_where_it_moved(caplog):
    caplog.set_level(logging.DEBUG, logger="court_booker.flow")
    app = moving_courts_app("details_other")
    booker = Booker(app, Config())

    booked = booker.book("11:00 - 12:00", TARGET)

    assert app.taps == [*FULL_ROUND[:5], "S10 - Sân tennis", *FULL_ROUND[5:]]
    assert app.calls == ["back"]
    assert "Tap 'S10 - Sân tennis' at (270, 852)" in caplog.text
    assert "The app opened another court than 'S10 - Sân tennis'" in caplog.text
    assert booked.shown_court == "S10 - Sân tennis"
    assert booker.commands == 16 + 4  # the other court's page, Back, the list, the tap


def test_court_moved_under_a_tap_that_opened_nothing_is_tapped_again_at_once(fake_time, caplog):
    caplog.set_level(logging.DEBUG, logger="court_booker.flow")
    app = moving_courts_app(("courts_moved", 2))

    Booker(app, Config()).book("11:00 - 12:00", TARGET)

    assert app.taps.count("S10 - Sân tennis") == 2
    assert "Tap 'S10 - Sân tennis' at (270, 852)" in caplog.text
    assert "moved on the court list under the tap" in caplog.text
    assert 0.6 <= fake_time[0] < 1.0  # not the 2 s a swallowed tap waits
    assert app.screen == "ticket"


def test_swallowed_court_tap_on_a_list_that_did_not_move_waits_two_seconds(fake_time):
    app = booking_app()
    app.swallow = {"S10 - Sân tennis": 1}

    Booker(app, Config()).book("11:00 - 12:00", TARGET)

    assert app.taps.count("S10 - Sân tennis") == 2
    assert fake_time[0] >= 2.0
    assert app.screen == "ticket"


def test_a_court_the_app_keeps_mixing_up_fails_the_round():
    app = moving_courts_app("details_other")
    app.taps_to[("courts_moved", "S10 - Sân tennis")] = "details_other"

    with pytest.raises(NavigationError, match=r"another court than 'S10 - Sân tennis' 5 time"):
        Booker(app, Config()).book("11:00 - 12:00", TARGET)

    assert app.taps.count("S10 - Sân tennis") == 5
    assert app.screen == "courts_moved"


def test_located_entry_makes_the_first_command_a_tap():
    app = booking_app()
    booker = Booker(app, Config())

    booker.locate_entry()
    app.ops.clear()
    booker.book("11:00 - 12:00", TARGET)

    assert app.ops[0] == ("click", "Sân Tennis")


def test_a_frozen_device_fails_the_round_instead_of_hanging_it():
    app = booking_app()
    frozen = threading.Event()
    app.taps_to[("details", "Tiếp tục")] = "frozen"  # MuMu froze after this tap on 2026-10-13
    app.screens["frozen"] = []
    reads = app.dump_hierarchy

    def dump_hierarchy(compressed=False):
        if app.screen == "frozen":
            frozen.wait()
        return reads(compressed)

    app.dump_hierarchy = dump_hierarchy
    booker = Booker(GuardedDevice(app, Watchdog(timeout=0.05)), Config())
    try:
        with pytest.raises(DeviceNotRespondingError, match="did not answer dump_hierarchy"):
            booker.book("11:00 - 12:00", TARGET)
    finally:
        frozen.set()

    assert app.taps == FULL_ROUND[:6]


def test_return_to_utilities_presses_back_from_ticket():
    app = booking_app(screen="ticket")

    Booker(app, Config()).return_to_utilities()

    assert app.calls == ["back"]
    assert app.screen == "utilities"


def test_return_after_a_refusal_presses_back_as_soon_as_each_screen_shows(fake_time):
    app = refusing_app(via_venue=True)
    # 2026-10-15: each Back shows a frame without labels, then the screen before.
    app.backs_to = {screen: ["loading", (before, 2)] for screen, before in app.backs_to.items()}
    app.screen = "notice"
    booker = Booker(app, Config())

    booker.return_to_utilities()

    assert app.screen == "utilities"
    # Notice, confirmation page, details, courts, venue, calendar.
    assert app.calls == ["back"] * 6
    assert booker.commands == 1 + 6 * 3  # per Back: the Back, the empty frame, the screen
    assert fake_time[0] < 0.5  # was 2 s per screen on the way


@pytest.mark.parametrize(
    "changed",
    [
        [*DAYS, *SLOTS, CONTINUE],  # the slots listed late
        [*DAYS, CONTINUE, node("6:01 AM", (6, 5, 50, 28), False)],  # the status bar's clock
    ],
)
def test_a_screen_that_changes_in_place_after_back_is_not_taken_for_the_next(changed):
    app = booking_app(screen="calendar")
    app.screens["calendar_changed"] = changed
    app.backs_to["calendar"] = [("calendar_changed", 1), ("utilities", 2)]

    Booker(app, Config()).return_to_utilities()

    assert app.calls == ["back"]  # a second Back would have left the utilities list
    assert app.taps == []
    assert app.screen == "utilities"


def test_a_back_the_app_missed_is_pressed_again_after_two_seconds(fake_time):
    app = booking_app(screen="details")
    press = app.press

    def miss_the_first_back(key):
        if app.calls:
            press(key)
        else:
            app.calls.append(key)

    app.press = miss_the_first_back

    Booker(app, Config()).return_to_utilities()

    assert app.calls == ["back"] * 4  # missed, then details, courts and calendar
    assert app.screen == "utilities"
    assert 2 <= fake_time[0] < 2.5


def test_return_to_utilities_warns_about_a_notice_it_closes(caplog):
    app = refusing_app()
    app.screen = "notice"

    Booker(app, Config()).return_to_utilities()

    assert f"Closing a notice of the app: {QUOTA_MESSAGE}" in caplog.text
    assert app.screen == "utilities"


def screen_of(nodes):
    return Screen([Node(desc, box, clickable) for desc, box, clickable in nodes])


def test_notice_text_reads_the_dialog_message():
    booker = Booker(booking_app(), Config())

    assert booker.notice_text(screen_of(NOTICE)) == QUOTA_MESSAGE


def test_notice_text_ignores_a_label_without_buttons_inside():
    booker = Booker(booking_app(), Config())
    tab = node("Thông báo", (400, 1500, 500, 1580))

    assert booker.notice_text(screen_of([node("Tiện ích", (200, 1500, 340, 1580)), tab])) is None
    assert booker.notice_text(screen_of(CONFIRM_PAGE)) is None


def test_select_slot_scrolls_until_slot_is_shown():
    # Small screen: the slot is not built at first, then clipped above the button.
    stages = [
        [node("10:00 - 11:00", (38, 780, 263, 860))],
        [node("10:00 - 11:00", (38, 700, 263, 780)), node("11:00 - 12:00", (277, 860, 502, 879))],
        [node("10:00 - 11:00", (38, 620, 263, 700)), node("11:00 - 12:00", (277, 700, 502, 780))],
    ]
    small_continue = node("Tiếp tục", (35, 885, 505, 951))
    app = FakeApp({"calendar": stages[0] + [small_continue]}, {}, {}, "calendar")

    def advance(app):
        app.screens["calendar"] = stages[min(app.swipes, 2)] + [small_continue]

    app.on_swipe = advance

    Booker(app, Config()).select_slot("11:00 - 12:00")

    assert app.swipes == 2
    assert app.ops[-1] == ("click", "11:00 - 12:00")
    # Swipes run down the middle of the portrait screen read from the dump.
    assert app.swipe_args[0][:4] == (270.0, 992.0, 270.0, 608.0)


def test_locate_checkbox_picks_small_node_level_with_caption():
    nodes = [*CONFIRM_PAGE, node("", (35, 1200, 79, 1244))]
    app = FakeApp({"confirm": nodes}, {}, {}, "confirm")
    screen = Screen.parse(app.dump_hierarchy())

    assert Booker(app, Config()).locate_checkbox(screen) == (57, 1345)


def test_prepare_restarts_app_and_stops_on_home():
    app = booking_app(screen="loading")

    Booker(app, Config()).prepare()

    assert app.calls == ["app_stop", "app_start"]
    assert app.taps == []
    assert app.screen == "home"


def test_prepare_keeps_running_app_and_goes_back_to_home():
    app = booking_app(screen="utilities")
    app.current = "com.vinhomes.resident"

    Booker(app, Config(restart_app=False)).prepare()

    assert app.calls == ["back"]
    assert app.taps == []
    assert app.screen == "home"


def test_located_entry_opens_the_utilities_list_from_home_then_reads_it_again():
    app = booking_app(screen="home")
    booker = Booker(app, Config())

    booker.locate_entry()  # warm-up: tap the home screen's utilities button
    booker.locate_entry()  # just before the start: read only
    app.ops.clear()
    booker.book("11:00 - 12:00", TARGET)

    assert app.taps[:2] == ["Tiện ích", "Sân Tennis"]
    assert app.ops[0] == ("click", "Sân Tennis")


def test_prepare_turns_animations_off_first():
    app = booking_app(screen="loading")

    Booker(app, Config()).prepare()

    assert app.shells == [
        "settings put global window_animation_scale 0; "
        "settings put global transition_animation_scale 0; "
        "settings put global animator_duration_scale 0"
    ]


def test_animations_that_stay_on_do_not_stop_the_run(caplog):
    class NoShellApp(FakeApp):
        def shell(self, command):
            raise RuntimeError("adb shell timeout")

    base = booking_app(screen="loading")
    app = NoShellApp(base.screens, base.taps_to, base.backs_to, "loading", base.launches_to)

    Booker(app, Config()).prepare()

    assert app.screen == "home"
    assert "Could not turn off animations" in caplog.text


def test_prepare_reports_logged_out_app():
    app = booking_app(screen="loading")
    app.launches_to = None

    with pytest.raises(AppNotReadyError, match="logged in"):
        Booker(app, Config(boot_timeout=1)).prepare()


def test_select_date_switches_to_next_month(caplog):
    day_31 = "31, Thứ Bảy, 31 tháng 10, 2026"
    day_nov_1 = "1, Chủ Nhật, 1 tháng 11, 2026"
    app = FakeApp(
        screens={
            "october": [
                node("Tháng sau", (490, 180, 530, 220)),
                node(day_31, (381, 344, 455, 402)),
            ],
            "november": [
                node("Tháng trước", (450, 180, 490, 220)),
                node(day_nov_1, (35, 344, 109, 402)),
            ],
            "slots": [],
        },
        taps_to={("october", "Tháng sau"): "november", ("november", day_nov_1): "slots"},
        backs_to={},
        screen="october",
    )
    booker = Booker(app, Config())
    caplog.set_level(logging.DEBUG, logger="court_booker")

    booker.select_date(booker.snapshot(), date(2026, 11, 1))

    assert app.taps == ["Tháng sau", day_nov_1]
    assert f"Date 2026-11-01 not shown; first day listed: {day_31!r}" in caplog.text


class OpeningBooker(Booker):
    """Booker whose screens are scripted: the slot opens on attempt ``opens_on``."""

    def __init__(self, opens_on, fully_booked=False):
        super().__init__(device=None, config=Config(open_retry_seconds=60))
        self.opens_on = opens_on
        self.fully_booked = fully_booked
        self.entries = 0
        self.backs = 0

    def tap_and_advance(self, screen, target, name, find_next):
        self.entries += 1
        return None, Screen([])

    def select_date(self, screen, target):
        if self.entries < self.opens_on:
            raise ElementNotFoundError(f"Date {target.isoformat()} is not bookable")

    def select_slot(self, slot):
        if self.fully_booked:
            raise SlotUnavailableError(f"Slot {slot} is fully booked")
        return Screen([])

    def return_to_utilities(self, screen=None):
        self.backs += 1
        return Screen([])


def fake_monotonic(monkeypatch, step):
    clock = iter(range(0, 100_000, step))
    monkeypatch.setattr(flow.time, "monotonic", lambda: next(clock))


def test_open_slot_reloads_until_open(monkeypatch):
    fake_monotonic(monkeypatch, step=1)
    booker = OpeningBooker(opens_on=3)

    booker.open_slot("18:00 - 19:00", date(2026, 10, 10))

    assert booker.entries == 3
    assert booker.backs == 3


def test_open_slot_gives_up_after_retry_window(monkeypatch):
    fake_monotonic(monkeypatch, step=20)
    booker = OpeningBooker(opens_on=1000)

    with pytest.raises(BookingNotOpenError, match="not open after 3 attempt"):
        booker.open_slot("18:00 - 19:00", date(2026, 10, 10))


def test_open_slot_does_not_retry_fully_booked(monkeypatch):
    fake_monotonic(monkeypatch, step=1)
    booker = OpeningBooker(opens_on=1, fully_booked=True)

    with pytest.raises(SlotUnavailableError):
        booker.open_slot("18:00 - 19:00", date(2026, 10, 10))
    assert booker.entries == 1


CLOSED_MESSAGE = (
    "Ban quản lý BQL Grand Park chỉ nhận đăng ký Sân Tennis từ 06:00 đến 21:00 mỗi ngày"
)
CLOSED_NOTICE = [  # 0.05 s after a tap on the utility at 05:59:59.244, 2026-10-19
    node("", (0, 0, 540, 1600)),
    node("Thông báo", (0, 33, 540, 1600), False),
    node(CLOSED_MESSAGE, (47, 758, 493, 817), False),
    node("Đóng", (47, 841, 493, 936)),
]


def early_app(notices):
    """Answer the first ``notices`` taps on the utility with the closed-hours notice."""
    app = booking_app()
    app.screens["closed"] = CLOSED_NOTICE
    app.backs_to["closed"] = "utilities"  # Back closed it on 2026-10-19
    click = app.click
    shown = [0]

    def click_early(x, y, label=""):
        if app.screen == "utilities":
            early = shown[0] < notices
            shown[0] += 1
            app.taps_to[("utilities", "Sân Tennis")] = "closed" if early else "calendar"
        click(x, y, label)

    app.click = click_early
    return app


def test_a_tap_before_the_opening_closes_the_notice_and_taps_again(caplog):
    caplog.set_level(logging.DEBUG, logger="court_booker.flow")
    app = early_app(notices=2)
    sink = MemorySink()
    booker = Booker(app, Config(), Reporter(sink))

    booker.book("11:00 - 12:00", TARGET)

    assert app.taps == ["Sân Tennis"] * 2 + FULL_ROUND
    assert app.calls == ["back"] * 2
    assert app.screen == "ticket"
    # Per notice: the tap, the notice, Back and the utilities list.
    assert booker.commands == 16 + 2 * 4
    assert sink.events[0].data == {"attempt": 3}
    logged = [(r.levelno, r.getMessage()) for r in caplog.records if "Not open yet" in r.message]
    message = f"Not open yet: {CLOSED_MESSAGE}; closing the notice and tapping again"
    assert logged == [(logging.INFO, message), (logging.DEBUG, message)]
    assert "Closing a notice" not in caplog.text  # expected here, so no warning


def test_a_notice_that_stays_fails_the_round_after_the_retry_window(monkeypatch):
    fake_monotonic(monkeypatch, step=5)
    app = early_app(notices=1_000_000)

    with pytest.raises(BookingNotOpenError, match=rf"attempt\(s\): {CLOSED_MESSAGE}$"):
        Booker(app, Config(open_retry_seconds=60)).book("11:00 - 12:00", TARGET)

    assert app.taps.count("Sân Tennis") > 1
    assert app.screen == "closed"
