"""Booking flow, one method per app screen.

Each screen is read with one hierarchy dump (:class:`~court_booker.screen.Screen`),
which lists every element with its bounds in about the time of a single element
query. Elements are found by accessibility label in that dump and tapped at their
coordinates, so waiting for the next screen and locating the next element are the
same query: a step costs one dump per poll plus one tap. No coordinates are kept
across screens. ``device`` is a :class:`uiautomator2.Device` or a test double with
``dump_hierarchy``, ``click``, ``press``, ``swipe`` and the app calls.
"""

from __future__ import annotations

import logging
import time
from datetime import date
from typing import Any, Callable, Optional, TypeVar

from court_booker.config import Config
from court_booker.errors import (
    AppNotReadyError,
    BookingNotOpenError,
    ElementNotFoundError,
    NavigationError,
    SlotUnavailableError,
)
from court_booker.geometry import (
    ANY_SLOT_PATTERN,
    DAY_PATTERN,
    day_pattern,
    is_checkbox_beside,
    month_index,
    month_index_from_label,
)
from court_booker.screen import Match, Node, Screen

logger = logging.getLogger(__name__)

T = TypeVar("T")
Finder = Callable[[Screen], Optional[T]]
"""Return what to act on in a screen, or ``None`` while it is not shown yet."""

_POLL_INTERVAL = 0.02
_NEXT_SCREEN_TIMEOUT = 2.0
_TAP_RETRIES = 5
_BACK_PRESSES = 8
_FIRST_DATE_WAIT = 1.5
_NEXT_DATE_WAIT = 0.8
_CHECKBOX_TIMEOUT = 0.8
_SETTLE_TIMEOUT = 1.0
_SWIPE_SECONDS = 0.25
_MIN_VISIBLE_RATIO = 0.6
"""A slot clipped to less than this share of a full slot's height is scrolled into view."""


class Booker:
    """Drive one booking round per call to :meth:`book`."""

    def __init__(self, device: Any, config: Config) -> None:
        self.device = device
        self.config = config
        self.commands = 0
        """Device commands sent so far; each is a round trip to the emulator."""
        self.last_screen = Screen([])
        self._entry: Screen | None = None

        labels = config.labels
        self.home = Match(desc=labels.home, clickable=True)
        self.utility = Match(desc=labels.utility, clickable=True)
        self.any_day = Match(pattern=DAY_PATTERN)
        self.any_slot = Match(pattern=ANY_SLOT_PATTERN)
        self.prev_month = Match(desc=labels.prev_month)
        self.next_month = Match(contains=labels.next_month)
        self.continue_button = Match(desc=labels.continue_, clickable=True)
        self.venue = Match(contains=config.venue_keyword) if config.venue_keyword else None
        self.court = Match(desc=config.court, clickable=True)
        self.any_court = Match(prefix=config.court, clickable=True)
        self.agree = Match(contains=labels.agree)
        self.confirm_button = Match(desc=labels.confirm, clickable=True)
        self.confirm_page = Match(desc=labels.confirm_page)

    # Public API -------------------------------------------------------------

    def prepare(self) -> None:
        """Open the app and stop on the utilities list, ready for the first round.

        With ``restart_app`` the app is stopped first, so a stale screen, popup or
        expired session from the previous day cannot get in the way.
        """
        package = self.config.package
        if self.config.restart_app:
            logger.info("Restarting %s", package)
            self.device.app_stop(package)
            self.device.app_start(package)
        elif self.device.app_current().get("package") != package:
            logger.info("Starting %s", package)
            self.device.app_start(package)

        found = self.wait_for(self._either(self.home, self.utility), self.config.boot_timeout)
        if found is None:
            raise AppNotReadyError(
                f"The app did not show {self.config.labels.home!r} or "
                f"{self.config.labels.utility!r} in {self.config.boot_timeout:.0f} s; "
                "check that it is logged in"
            )
        try:
            self.return_to_utilities(found[1])
        except NavigationError as exc:
            raise AppNotReadyError(str(exc)) from exc
        logger.info("Ready on the utilities list")

    def locate_entry(self) -> None:
        """Read the utilities list just before the start time.

        The first round then taps the utility with a single command at the start
        time, and the read wakes the device connection after the long wait.
        """
        self._entry = self.return_to_utilities()
        logger.debug("Located %r ahead of the start time", self.config.labels.utility)

    def book(self, slot: str, target: date, dry_run: bool = False) -> None:
        """Book ``slot`` on ``target``, starting from the home or utilities screen."""
        labels = self.config.labels
        screen = self.open_slot(slot, target)
        court, screen = self.tap_and_advance(
            screen, self.continue_button, labels.continue_, self._find_court
        )
        if self.venue is not None and not self.any_court(court):
            court, screen = self.tap_and_advance(
                screen, self.venue, self.config.venue_keyword, self._find_court
            )
        if labels.fully_booked in court.desc:
            raise SlotUnavailableError(f"Court {self.config.court} is fully booked")
        _, screen = self.tap_and_advance(
            screen, self.court, self.config.court, self._finder(self.continue_button)
        )
        point, _ = self.tap_and_advance(
            screen, self.continue_button, labels.continue_, self.locate_checkbox
        )
        self.accept_and_confirm(point, dry_run)

    def open_slot(self, slot: str, target: date) -> Screen:
        """Open the calendar and select ``target`` and ``slot``.

        Returns the calendar screen read before the slot was tapped, which also
        holds the continue button. Right at the opening time the server may not
        list the new date or slot yet, so the calendar is left and re-entered to
        reload it until ``open_retry_seconds`` have passed. A fully booked slot
        fails at once.
        """
        deadline = time.monotonic() + self.config.open_retry_seconds
        attempt = 1
        while True:
            screen = self._entry if self._entry is not None else self.return_to_utilities()
            self._entry = None
            _, screen = self.tap_and_advance(
                screen, self.utility, self.config.labels.utility, self._find_calendar
            )
            try:
                self.select_date(screen, target)
                return self.select_slot(slot)
            except ElementNotFoundError as exc:
                if time.monotonic() >= deadline:
                    raise BookingNotOpenError(
                        f"{target.isoformat()} {slot} not open after {attempt} attempt(s): {exc}"
                    ) from exc
                logger.info("Not open yet (%s); reloading the calendar", exc)
            attempt += 1

    def return_to_utilities(self, screen: Screen | None = None) -> Screen:
        """Navigate to the utilities list from the home, ticket or any inner screen."""
        if screen is None:
            screen = self.snapshot()
        for _ in range(_BACK_PRESSES):
            if screen.find(self.utility):
                return screen
            if screen.find(self.home):
                _, screen = self.tap_and_advance(
                    screen, self.home, self.config.labels.home, self._finder(self.utility)
                )
                return screen
            self.press_back()
            found = self.wait_for(self._either(self.utility, self.home), _NEXT_SCREEN_TIMEOUT)
            screen = found[1] if found is not None else self.last_screen
        raise NavigationError("Could not return to the utilities list")

    # Navigation -------------------------------------------------------------

    def tap_and_advance(
        self, screen: Screen, target: Match, name: str, find_next: Finder[T]
    ) -> tuple[T, Screen]:
        """Tap ``target`` on ``screen`` and return what ``find_next`` finds on the next one.

        A tap swallowed by a lagging app is retried while ``target`` is still shown.
        """
        node = screen.find(target)
        if node is None:
            raise ElementNotFoundError(f"Button not found: {name!r}")
        for attempt in range(_TAP_RETRIES):
            if node is not None:
                self.tap(node)
            found = self.wait_for(find_next, _NEXT_SCREEN_TIMEOUT)
            if found is not None:
                logger.info("Tapped %r", name)
                return found
            node = self.last_screen.find(target)
            logger.debug("Next screen missing after %r (attempt %d)", name, attempt + 2)
        raise NavigationError(f"Tapped {name!r} but the next screen did not appear")

    def wait_for(
        self, find: Finder[T], timeout: float, screen: Screen | None = None
    ) -> tuple[T, Screen] | None:
        """Read the screen until ``find`` returns a value; ``None`` after ``timeout``.

        ``screen``, if given, is checked first without reading the device again.
        """
        deadline = time.monotonic() + timeout
        while True:
            if screen is None:
                screen = self.snapshot()
            found = find(screen)
            if found is not None:
                return found, screen
            if time.monotonic() >= deadline:
                return None
            time.sleep(_POLL_INTERVAL)
            screen = None

    # Calendar screen --------------------------------------------------------

    def select_date(self, screen: Screen, target: date) -> None:
        """Tap ``target`` in the calendar shown on ``screen``, switching month if needed."""
        match = Match(pattern=day_pattern(target))
        target_month = month_index(target.year, target.month)
        current: Screen | None = screen
        for attempt in range(5):
            wait = _FIRST_DATE_WAIT if attempt == 0 else _NEXT_DATE_WAIT
            found = self.wait_for(self._finder(match), wait, current)
            if found is not None:
                self.tap(found[0])
                logger.info("Selected date %s", target.isoformat())
                return
            first_day = self.last_screen.find(self.any_day)
            logger.debug(
                "Date %s not shown; first day listed: %r",
                target.isoformat(),
                first_day.desc if first_day else None,
            )
            shown = None if first_day is None else month_index_from_label(first_day.desc)
            forward = attempt % 2 == 0 if shown is None else shown < target_month
            self._switch_month(self.last_screen, forward)
            current = None
        raise ElementNotFoundError(f"Date {target.isoformat()} is not bookable")

    def select_slot(self, slot: str) -> Screen:
        """Tap ``slot`` once the list shows it, scrolling only while it is hidden.

        Returns the screen read before the tap.
        """
        match = Match(prefix=slot)
        deadline = time.monotonic() + self.config.timeout
        swipes = 0
        screen: Screen | None = None
        while True:
            remaining = max(0.0, deadline - time.monotonic())
            found = self.wait_for(self._finder(self.any_slot), remaining, screen)
            if found is None:
                break
            screen = found[1]
            node = screen.find(match)
            if node is None:
                down = True
            else:
                if self.config.labels.fully_booked in node.desc:
                    raise SlotUnavailableError(f"Slot {slot} is fully booked")
                position = self._visibility(screen, node)
                if position == "visible":
                    self.tap(node)
                    logger.info("Selected slot %s (%d swipe(s))", slot, swipes)
                    return screen
                down = position == "below"
            if swipes >= self.config.max_swipes or time.monotonic() >= deadline:
                break
            self._scroll(screen, down)
            swipes += 1
            screen = self._settled_screen()
        raise ElementNotFoundError(f"Slot {slot} not found after {swipes} swipe(s)")

    # Confirmation screen ----------------------------------------------------

    def locate_checkbox(self, screen: Screen) -> tuple[int, int] | None:
        """Return the tap point of the consent checkbox, or ``None`` if not rendered.

        The checkbox has no label; it is the small node beside its caption,
        preferring clickable and smaller nodes. Nodes that are not level with the
        caption are never returned.
        """
        caption = screen.find(self.agree)
        if caption is None:
            return None
        width, _ = screen.size
        candidates = [
            node for node in screen.nodes if is_checkbox_beside(node.box, caption.box, width)
        ]
        if not candidates:
            return None
        node = min(candidates, key=lambda n: (not n.clickable, _area(n)))
        logger.debug("Checkbox found beside caption at %s", node.box)
        return node.center

    def accept_and_confirm(self, point: tuple[int, int], dry_run: bool) -> None:
        """Tick the consent checkbox at ``point`` and submit the booking.

        The confirm button only becomes clickable once the box is ticked, which
        verifies the tick.
        """
        deadline = time.monotonic() + self.config.timeout
        while True:
            self.tap_point(*point)
            found = self.wait_for(self._finder(self.confirm_button), _CHECKBOX_TIMEOUT)
            if found is not None:
                break
            if time.monotonic() >= deadline:
                raise NavigationError("Checkbox tapped but the confirm button stayed disabled")
            point = self.locate_checkbox(self.last_screen) or point
        logger.info("Accepted terms")

        if dry_run:
            logger.info("Dry run: skipping final confirmation")
            return
        self.tap(found[0])
        if self.wait_for(self._absent(self.confirm_page), self.config.timeout) is None:
            raise NavigationError("Confirmation submitted but the ticket screen did not appear")
        logger.info("Booking confirmed")

    # Device commands --------------------------------------------------------

    def snapshot(self) -> Screen:
        """Read every element of the current screen with one command."""
        self.commands += 1
        self.last_screen = Screen.parse(self.device.dump_hierarchy(compressed=False))
        return self.last_screen

    def tap(self, node: Node) -> None:
        self.tap_point(*node.center)

    def tap_point(self, x: float, y: float) -> None:
        self.commands += 1
        self.device.click(x, y)

    def press_back(self) -> None:
        self.commands += 1
        self.device.press("back")

    # Helpers ----------------------------------------------------------------

    def _finder(self, match: Match) -> Finder[Node]:
        return lambda screen: screen.find(match)

    def _either(self, first: Match, second: Match) -> Finder[Node]:
        return lambda screen: screen.find(first) or screen.find(second)

    def _absent(self, match: Match) -> Finder[bool]:
        return lambda screen: True if screen.find(match) is None else None

    def _find_calendar(self, screen: Screen) -> Node | None:
        return (
            screen.find(self.any_day)
            or screen.find(self.prev_month)
            or screen.find(self.next_month)
        )

    def _find_court(self, screen: Screen) -> Node | None:
        court = screen.find(self.any_court)
        if court is None and self.venue is not None:
            return screen.find(self.venue)
        return court

    def _visibility(self, screen: Screen, node: Node) -> str:
        """Return ``visible``, ``below`` or ``above`` relative to the tappable area.

        Dump bounds are clipped to what is shown, so a partly hidden slot is
        shorter than a full one. The sticky bottom button counts as hidden area.
        """
        _, height = screen.size
        button = screen.find(Match(desc=self.config.labels.continue_))
        bottom_limit = button.box[1] if button is not None else height
        full_height = max(n.height for n in screen.find_all(self.any_slot))
        if node.box[3] <= bottom_limit and node.height >= full_height * _MIN_VISIBLE_RATIO:
            return "visible"
        return "below" if node.center[1] > height / 2 else "above"

    def _scroll(self, screen: Screen, down: bool) -> None:
        width, height = screen.size
        start, end = (0.62, 0.38) if down else (0.38, 0.62)
        self.commands += 1
        self.device.swipe(width * 0.5, height * start, width * 0.5, height * end, _SWIPE_SECONDS)

    def _settled_screen(self) -> Screen:
        """Read the screen until the slot list stops moving after a swipe."""
        deadline = time.monotonic() + _SETTLE_TIMEOUT
        previous = None
        while True:
            screen = self.snapshot()
            boxes = [node.box for node in screen.find_all(self.any_slot)]
            if boxes == previous or time.monotonic() >= deadline:
                return screen
            previous = boxes
            time.sleep(_POLL_INTERVAL)

    def _switch_month(self, screen: Screen, forward: bool) -> None:
        button = screen.find(self.next_month if forward else self.prev_month)
        if button is not None:
            self.tap(button)
        else:
            x_ratio, y_ratio = self.config.next_month_xy if forward else self.config.prev_month_xy
            width, height = screen.size
            self.tap_point(width * x_ratio, height * y_ratio)
        logger.debug("Switched to %s month", "next" if forward else "previous")


def _area(node: Node) -> int:
    left, top, right, bottom = node.box
    return (right - left) * (bottom - top)
