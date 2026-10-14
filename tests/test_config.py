from pathlib import Path

import pytest

from court_booker.config import (
    Config,
    ConfigError,
    ensure_config,
    load_config,
    save_config,
    validate_config,
)


def test_missing_file_uses_defaults(tmp_path):
    config = load_config(tmp_path / "missing.toml")
    assert config.labels.home == "Tiện ích"


def test_example_config_lists_the_default_labels():
    example = Path(__file__).resolve().parents[1] / "config.example.toml"
    assert load_config(example).labels == Config().labels


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


def test_saved_config_loads_back_the_same(tmp_path):
    config = Config(slots=["19:00 - 20:00", "18:00 - 19:00"], days_ahead=1, wake_at="05:50")
    config.next_month_xy = (0.9, 0.12)
    config.labels.continue_ = "Tiếp tục nha"
    path = tmp_path / "CourtBooker" / "config.toml"

    save_config(config, path)

    assert load_config(path) == config
    assert 'continue = "Tiếp tục nha"' in path.read_text(encoding="utf-8")
    assert not (tmp_path / "CourtBooker" / "config.toml.tmp").exists()


def test_invalid_config_is_not_saved(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text('slots = ["18:00 - 19:00"]\n', encoding="utf-8")

    with pytest.raises(ConfigError, match="wake_at must be before start_at"):
        save_config(Config(wake_at="06:30"), path)

    assert path.read_text(encoding="utf-8") == 'slots = ["18:00 - 19:00"]\n'


def test_ensure_config_writes_the_defaults_once(tmp_path):
    path = tmp_path / "config.toml"

    assert ensure_config(path) == path
    assert load_config(path) == Config()

    path.write_text('slots = ["18:00 - 19:00"]\n', encoding="utf-8")
    ensure_config(path)
    assert load_config(path).slots == ["18:00 - 19:00"]
