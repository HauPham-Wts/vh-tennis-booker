"""The languages the Vinhomes app shows, and how each one labels its screens.

The app shows Vietnamese or English, as set in the app. Both lay out every screen the same
way; only the labels and the calendar's day labels differ. The court names and the booked
date and time on the confirmation page and the ticket read the same in both (2026-10-20), so
they are not part of a language. Kept free of device access for unit tests.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

from court_booker.config import Labels
from court_booker.geometry import month_index

ENGLISH_LABELS = Labels(  # read from the app in English on 2026-10-20
    home="Utilities",
    utility="Tennis",
    continue_="Next",
    confirm="Confirm",
    confirm_page="Confirm registration",
    prev_month="Previous month",  # not shown: the month buttons have no label in either language
    next_month="Next month",
    agree="I have read",  # the caption reads "I have read, understood, and agree to "
    fully_booked="Full",
    notice="Notification",
    booked_time="Schedule time",
    booked_place="Place/service",
    ticket="Booking details",
    processing="Processing",
    registered="Registered",
)
"""The English labels. The Vietnamese ones are the config's ``[labels]``."""

ENGLISH_MONTHS = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)


@dataclass(frozen=True)
class AppLanguage:
    """The labels of the app in one language, and how its calendar names a day."""

    name: str
    labels: Labels
    day_label: str
    """A calendar day's label with ``{day}``, ``{weekday}``, ``{month}`` and ``{year}`` in it,
    such as ``2, Thứ Sáu, 2 tháng 10, 2026``; the rest of it has no regex syntax."""
    months: tuple[str, ...]
    """What stands for ``{month}``, January to December."""

    @property
    def any_day(self) -> str:
        """Return a regex matching the label of any calendar day."""
        return self._day_regex(r"\d{1,2}", f"(?:{self._any_month()})", r"\d{4}")

    def day_pattern(self, target: date) -> str:
        """Return a regex matching the label of ``target`` only."""
        month = re.escape(self.months[target.month - 1])
        return self._day_regex(str(target.day), month, str(target.year))

    def month_index_from_label(self, label: str) -> int | None:
        """Return the month index of the calendar day labelled ``label``, or ``None``."""
        regex = self._day_regex(r"\d{1,2}", f"(?P<month>{self._any_month()})", r"(?P<year>\d{4})")
        match = re.fullmatch(regex, label or "", re.DOTALL)
        if match is None:
            return None
        return month_index(int(match["year"]), self.months.index(match["month"]) + 1)

    def _any_month(self) -> str:
        return "|".join(re.escape(month) for month in self.months)

    def _day_regex(self, day: str, month: str, year: str) -> str:
        return self.day_label.format(day=day, weekday=".*", month=month, year=year)


def app_languages(labels: Labels) -> tuple[AppLanguage, ...]:
    """Return the app's languages: Vietnamese with ``labels``, the config's, then English."""
    return (
        AppLanguage(
            "Vietnamese",
            labels,
            "{day}, {weekday}, {day} tháng {month}, {year}",
            tuple(str(month) for month in range(1, 13)),
        ),
        AppLanguage(
            "English", ENGLISH_LABELS, "{day}, {weekday}, {month} {day}, {year}", ENGLISH_MONTHS
        ),
    )
