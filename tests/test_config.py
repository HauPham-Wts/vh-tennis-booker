import pytest

from court_booker.config import Config, ConfigError, load_config, validate_config


def test_missing_file_uses_defaults(tmp_path):
    config = load_config(tmp_path / "missing.toml")
    assert config.labels.home == "Tiện ích"


def test_file_overrides_defaults(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text('slots = ["18:00 - 19:00"]\n[labels]\ncontinue = "Next"\n', encoding="utf-8")
    config = load_config(path)
    assert config.slots == ["18:00 - 19:00"]
    assert config.labels.continue_ == "Next"


def test_unknown_key_is_rejected(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text("slot = 1\n", encoding="utf-8")
    with pytest.raises(ConfigError):
        load_config(path)


def test_defaults_are_valid():
    assert validate_config(Config()) == []


@pytest.mark.parametrize(
    ("changes", "problem"),
    [
        ({"slots": []}, "choose at least one slot"),
        ({"slots": ["18:00-19:00"]}, "slot '18:00-19:00' must look like '18:00 - 19:00'"),
        ({"slots": ["18:00 - 19:00", "18:00 - 19:00"]}, "a slot is listed twice"),
        ({"court": " "}, "court is empty"),
        ({"days_ahead": 3}, "days_ahead must be 0 to 2"),
        ({"wake_at": "6:00 AM"}, "Invalid wake_at '6:00 AM'; use HH:MM or HH:MM:SS"),
        ({"wake_at": "06:05"}, "wake_at must be before start_at"),
        ({"timeout": 0}, "timeout must be positive"),
        ({"open_retry_seconds": -1}, "open_retry_seconds must not be negative"),
        ({"next_month_xy": (1.2, 0.1)}, "next_month_xy must be two screen ratios between 0 and 1"),
    ],
)
def test_invalid_values_are_reported(changes, problem):
    config = Config()
    for name, value in changes.items():
        setattr(config, name, value)

    assert validate_config(config) == [problem]
