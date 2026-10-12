"""Flow tests against a scripted fake app; no emulator required."""

import logging
from datetime import date
from xml.sax.saxutils import quoteattr

import pytest

import court_booker.flow as flow
from court_booker.config import Config
from court_booker.errors import (
    AppNotReadyError,
    BookingNotOpenError,
    ElementNotFoundError,
    SlotUnavailableError,
)
from court_booker.flow import Booker
from court_booker.screen import Screen

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
CONFIRM_PAGE = [
    node("Xác nhận đăng ký", (145, 52, 395, 89), False),
    node("", (0, 1292, 540, 1465)),
    node("", CHECKBOX),
    node("Tôi đã hiểu và đồng ý với ", (79, 1322, 313, 1355), False),
]


class FakeApp:
    """Scripted app: each screen is a list of nodes; taps and Back switch screens.

    A switch takes effect at once, like a tap the app handles before the next
    one, or after ``delay`` dumps, like a screen that is still loading.
    """

    def __init__(self, screens, taps_to, backs_to, screen, launches_to=None, current=""):
        self.screens = screens
        self.taps_to = taps_to
        self.backs_to = backs_to
        self.screen = screen
        self.launches_to = launches_to
        self.current = current
        self.pending = None
        self.swallow = {}
        self.on_swipe = None
        self.ops = []
        self.taps = []
        self.calls = []
        self.swipes = 0
        self.swipe_args = []

    def go(self, target):
        name, delay = (target, 0) if isinstance(target, str) else target
        if delay == 0:
            self.screen, self.pending = name, None
        else:
            self.pending = [name, delay]

    def dump_hierarchy(self, compressed=False):
        self.ops.append("dump")
        if self.pending is not None:
            self.pending[1] -= 1
            if self.pending[1] <= 0:
                self.screen, self.pending = self.pending[0], None
        children = "".join(
            f"<node content-desc={quoteattr(desc, {chr(10): '&#10;'})} "
            f'bounds="[{box[0]},{box[1]}][{box[2]},{box[3]}]" '
            f'clickable="{"true" if clickable else "false"}" />'
            for desc, box, clickable in self.screens[self.screen]
        )
        root = f'<node content-desc="" bounds="[0,0][{WIDTH},{HEIGHT}]" clickable="false">'
        return f"<hierarchy>{root}{children}</node></hierarchy>"

    def click(self, x, y):
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


def booking_app(screen="utilities", courts=COURTS, via_venue=False, slot_delay=0):
    screens = {
        "loading": [],
        "home": [node("Tiện ích", (200, 1500, 340, 1580))],
        "utilities": [node("Sân Tennis", (35, 300, 505, 360))],
        "calendar": [*DAYS, CONTINUE],
        "calendar_slots": DAYS + SLOTS + [CONTINUE],
        "calendar_selected": DAYS + SLOTS + [CONTINUE],
        "venue": [node("Origami Grand Park", (35, 600, 505, 700))],
        "courts": courts,
        "details": [node("S10 - Sân tennis", (116, 975, 274, 1004), False), CONTINUE],
        "confirm": [*CONFIRM_PAGE, node("Xác nhận", (35, 1490, 505, 1584), False)],
        "confirm_ticked": [*CONFIRM_PAGE, node("Xác nhận", (35, 1490, 505, 1584))],
        "ticket": [node("Đăng ký thành công", (35, 200, 505, 260), False)],
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
        "ticket": "utilities",
        "confirm": "details",
        "confirm_ticked": "details",
        "details": "courts",
        "courts": "calendar_selected",
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


def test_book_waits_for_slow_slot_list():
    app = booking_app(slot_delay=5)

    Booker(app, Config()).book("11:00 - 12:00", TARGET)

    assert app.taps == FULL_ROUND


def test_dry_run_stops_before_final_confirmation():
    app = booking_app()

    Booker(app, Config()).book("11:00 - 12:00", TARGET, dry_run=True)

    assert app.taps == FULL_ROUND[:-1]
    assert app.screen == "confirm_ticked"


def test_book_taps_venue_screen_when_shown():
    app = booking_app(via_venue=True)

    Booker(app, Config()).book("11:00 - 12:00", TARGET)

    assert app.taps[4] == "Origami Grand Park"
    assert app.screen == "ticket"


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


def test_located_entry_makes_the_first_command_a_tap():
    app = booking_app()
    booker = Booker(app, Config())

    booker.locate_entry()
    app.ops.clear()
    booker.book("11:00 - 12:00", TARGET)

    assert app.ops[0] == ("click", "Sân Tennis")


def test_return_to_utilities_presses_back_from_ticket():
    app = booking_app(screen="ticket")

    Booker(app, Config()).return_to_utilities()

    assert app.calls == ["back"]
    assert app.screen == "utilities"


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


def test_prepare_restarts_app_and_stops_on_utilities():
    app = booking_app(screen="loading")

    Booker(app, Config()).prepare()

    assert app.calls == ["app_stop", "app_start"]
    assert app.taps == ["Tiện ích"]
    assert app.screen == "utilities"


def test_prepare_keeps_running_app_without_restart():
    app = booking_app(screen="utilities")
    app.current = "com.vinhomes.resident"

    Booker(app, Config(restart_app=False)).prepare()

    assert app.calls == []
    assert app.taps == []


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
