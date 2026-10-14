import re
from datetime import date

from court_booker.geometry import (
    day_pattern,
    is_checkbox_beside,
    is_inside,
    month_index,
    month_index_from_label,
    parse_bounds,
)

SCREEN_WIDTH = 540
CAPTION = (79, 739, 313, 772)  # captured from the device at 540x960
CHECKBOX = (35, 740, 79, 784)


def test_parse_bounds():
    assert parse_bounds("[35,740][79,784]") == CHECKBOX
    assert parse_bounds("") is None


def test_is_inside_includes_the_edges():
    dialog = (0, 33, 540, 1600)
    assert is_inside((47, 841, 493, 936), dialog)
    assert is_inside(dialog, dialog)
    assert not is_inside((6, 5, 50, 28), dialog)  # the status bar clock above it


def test_checkbox_beside_caption_is_accepted():
    assert is_checkbox_beside(CHECKBOX, CAPTION, SCREEN_WIDTH)


def test_unrelated_nodes_are_rejected():
    back_button = (0, 40, 60, 100)
    container = (0, 721, 540, 869)
    full_screen = (0, 0, 540, 960)
    for box in (back_button, container, full_screen):
        assert not is_checkbox_beside(box, CAPTION, SCREEN_WIDTH)


def test_checkbox_detection_scales_with_resolution():
    factor = 1440 / SCREEN_WIDTH

    def scale(box):
        return tuple(int(v * factor) for v in box)

    assert is_checkbox_beside(scale(CHECKBOX), scale(CAPTION), 1440)


def test_day_pattern_matches_exact_day_only():
    pattern = day_pattern(date(2026, 10, 3))
    assert re.fullmatch(pattern, "3, Thứ Bảy, 3 tháng 10, 2026")
    assert not re.fullmatch(pattern, "13, Thứ Ba, 13 tháng 10, 2026")


def test_day_pattern_across_month_and_year():
    assert re.fullmatch(day_pattern(date(2026, 11, 1)), "1, Chủ Nhật, 1 tháng 11, 2026")
    assert re.fullmatch(day_pattern(date(2027, 1, 1)), "1, Thứ Sáu, 1 tháng 1, 2027")


def test_month_index_from_label():
    assert month_index_from_label("2, Thứ Sáu, 2 tháng 10, 2026") == month_index(2026, 10)
    assert month_index_from_label("no date") is None
