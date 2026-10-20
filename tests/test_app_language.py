import re
from datetime import date

from court_booker.app_language import app_languages
from court_booker.config import Labels
from court_booker.geometry import month_index

[VIETNAMESE] = app_languages(Labels())


def test_vietnamese_uses_the_config_labels():
    labels = Labels(utility="Sân tennis")

    assert app_languages(labels)[0].labels is labels


def test_day_pattern_matches_exact_day_only():
    pattern = VIETNAMESE.day_pattern(date(2026, 10, 3))
    assert re.fullmatch(pattern, "3, Thứ Bảy, 3 tháng 10, 2026")
    assert not re.fullmatch(pattern, "13, Thứ Ba, 13 tháng 10, 2026")
    assert not re.fullmatch(pattern, "3, Thứ Ba, 3 tháng 11, 2026")


def test_day_pattern_across_month_and_year():
    assert re.fullmatch(VIETNAMESE.day_pattern(date(2026, 11, 1)), "1, Chủ Nhật, 1 tháng 11, 2026")
    assert re.fullmatch(VIETNAMESE.day_pattern(date(2027, 1, 1)), "1, Thứ Sáu, 1 tháng 1, 2027")


def test_any_day_matches_days_only():
    assert re.fullmatch(VIETNAMESE.any_day, "2, Thứ Sáu, 2 tháng 10, 2026")
    assert re.fullmatch(VIETNAMESE.any_day, "31, Thứ Bảy, 31 tháng 12, 2026")
    assert not re.fullmatch(VIETNAMESE.any_day, "18:00 - 19:00")
    assert not re.fullmatch(VIETNAMESE.any_day, "Chọn năm")


def test_month_index_from_label():
    label = "2, Thứ Sáu, 2 tháng 10, 2026"
    assert VIETNAMESE.month_index_from_label(label) == month_index(2026, 10)
    assert VIETNAMESE.month_index_from_label("1, Thứ Sáu, 1 tháng 1, 2027") == month_index(2027, 1)
    assert VIETNAMESE.month_index_from_label("no date") is None
