"""Pure helpers for element bounds and date matching.

Kept free of device access so they can be unit-tested without an emulator.
"""

from __future__ import annotations

import re
from datetime import date

Box = tuple[int, int, int, int]
"""Element bounds as ``(left, top, right, bottom)`` in pixels."""

DAY_PATTERN = r"\d{1,2}, .*, \d{1,2} tháng \d{1,2}, \d{4}"
"""Accessibility label of a selectable calendar day, e.g. ``2, Thứ Sáu, 2 tháng 10, 2026``."""

ANY_SLOT_PATTERN = r"(?s)\d{2}:\d{2} - \d{2}:\d{2}.*"
"""Accessibility label of any time slot, available or fully booked."""

_CHECKBOX_MAX_SIZE_RATIO = 0.2
_CHECKBOX_GAP_RATIO = 0.02


def parse_bounds(text: str) -> Box | None:
    """Parse a uiautomator ``bounds`` attribute such as ``[35,740][79,784]``."""
    nums = [int(n) for n in re.findall(r"-?\d+", text or "")]
    if len(nums) != 4:
        return None
    return nums[0], nums[1], nums[2], nums[3]


def center(box: Box) -> tuple[int, int]:
    """Return the center point of ``box``."""
    left, top, right, bottom = box
    return (left + right) // 2, (top + bottom) // 2


def is_inside(box: Box, outer: Box) -> bool:
    """Return whether ``box`` lies within ``outer``, edges included."""
    left, top, right, bottom = box
    outer_left, outer_top, outer_right, outer_bottom = outer
    return (
        outer_left <= left and outer_top <= top and right <= outer_right and bottom <= outer_bottom
    )


def is_checkbox_beside(box: Box, label: Box, screen_width: int) -> bool:
    """Return whether ``box`` is a plausible checkbox for the caption ``label``.

    A checkbox must be small, sit to the left of the caption and overlap it
    vertically. Thresholds scale with the screen width.
    """
    left, top, right, bottom = box
    label_left, label_top, _, label_bottom = label
    max_size = screen_width * _CHECKBOX_MAX_SIZE_RATIO
    gap = screen_width * _CHECKBOX_GAP_RATIO

    is_small = 0 < right - left <= max_size and 0 < bottom - top <= max_size
    is_left_of_label = right <= label_left + gap
    is_same_row = top < label_bottom and bottom > label_top
    return is_small and is_left_of_label and is_same_row


def day_pattern(target: date) -> str:
    """Return a regex matching the accessibility label of ``target`` only."""
    return f"{target.day}, .*, {target.day} tháng {target.month}, {target.year}"


def month_index(year: int, month: int) -> int:
    """Return a monotonically increasing index for a calendar month."""
    return year * 12 + month


def month_index_from_label(label: str) -> int | None:
    """Extract the month index from a calendar-day accessibility label."""
    match = re.search(r"tháng (\d{1,2}), (\d{4})", label or "")
    if match is None:
        return None
    return month_index(int(match.group(2)), int(match.group(1)))
