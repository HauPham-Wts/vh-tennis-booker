import re
from dataclasses import fields
from datetime import date

import pytest

from court_booker.app_language import ENGLISH_LABELS, app_languages
from court_booker.config import ConfigError, Labels
from court_booker.geometry import month_index

VIETNAMESE, ENGLISH = app_languages(Labels())


def test_every_english_label_is_set():
    for item in fields(Labels):
        english = getattr(ENGLISH_LABELS, item.name)
        assert english and english != getattr(Labels(), item.name), item.name


def test_english_dates_match_the_exact_day_only():
    pattern = ENGLISH.day_pattern(date(2026, 10, 3))
    assert re.fullmatch(pattern, "3, Saturday, October 3, 2026")
    assert not re.fullmatch(pattern, "13, Tuesday, October 13, 2026")
    assert not re.fullmatch(pattern, "3, Tuesday, November 3, 2026")
    assert not re.fullmatch(pattern, "3, Thứ Bảy, 3 tháng 10, 2026")


def test_english_dates_across_month_and_year():
    assert re.fullmatch(ENGLISH.day_pattern(date(2026, 10, 21)), "21, Wednesday, October 21, 2026")
    assert re.fullmatch(ENGLISH.day_pattern(date(2026, 11, 1)), "1, Sunday, November 1, 2026")
    assert re.fullmatch(ENGLISH.day_pattern(date(2027, 1, 1)), "1, Friday, January 1, 2027")


@pytest.mark.parametrize(
    ("label", "vietnamese", "english"),
    [
        ("2, Thứ Sáu, 2 tháng 10, 2026", True, False),
        ("21, Wednesday, October 21, 2026", False, True),
        ("18:00 - 19:00\nFull", False, False),
        ("Select year", False, False),
    ],
)
def test_any_day_matches_the_days_of_its_language(label, vietnamese, english):
    assert bool(re.fullmatch(VIETNAMESE.any_day, label, re.DOTALL)) is vietnamese
    assert bool(re.fullmatch(ENGLISH.any_day, label, re.DOTALL)) is english


def test_english_month_index_from_label():
    label = "21, Wednesday, October 21, 2026"
    assert ENGLISH.month_index_from_label(label) == month_index(2026, 10)
    assert ENGLISH.month_index_from_label("1, Friday, January 1, 2027") == month_index(2027, 1)
    assert ENGLISH.month_index_from_label("2, Thứ Sáu, 2 tháng 10, 2026") is None


def test_vietnamese_uses_the_config_labels():
    labels = Labels(home="Trang chủ", utility="Sân tennis")

    assert app_languages(labels)[0].labels == labels


@pytest.mark.parametrize(
    ("sport", "vietnamese", "english"),
    [
        ("tennis", "Sân Tennis", "Tennis"),
        ("table-tennis", "Sân bóng bàn", ""),
        ("pickleball", "Sân Pickleball", ""),
        ("badminton", "Sân cầu lông", ""),
    ],
)
def test_each_language_taps_the_tile_of_the_sport(sport, vietnamese, english):
    languages = app_languages(Labels(), sport)

    assert [language.labels.utility for language in languages] == [vietnamese, english]


def test_a_utility_label_set_by_hand_wins_over_the_sport():
    assert app_languages(Labels(utility="Sân mới"), "badminton")[0].labels.utility == "Sân mới"


def test_an_unknown_sport_is_refused():
    with pytest.raises(ConfigError, match="Unknown sport 'golf'"):
        app_languages(Labels(), "golf")


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
