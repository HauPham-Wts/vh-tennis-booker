import re
from pathlib import Path

import pytest

from court_booker.config import (
    Config,
    ConfigError,
    config_to_dict,
    ensure_config,
    instance_config,
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
        ({"wake_at": "6:00 AM"}, "Invalid wake_at '6:00 AM'; use HH:MM or HH:MM:SS"),
        ({"wake_at": "06:05"}, "wake_at must be before start_at"),
        ({"timeout": 0}, "timeout must be positive"),
        ({"open_retry_seconds": -1}, "open_retry_seconds must not be negative"),
        ({"warm_up_seconds": 2}, "warm_up_seconds must be 5 to 600 seconds"),
        ({"warm_up_seconds": 900}, "warm_up_seconds must be 5 to 600 seconds"),
        ({"next_month_xy": (1.2, 0.1)}, "next_month_xy must be two screen ratios between 0 and 1"),
        ({"notification_language": "fr"}, "notification_language must be one of vi, en"),
    ],
)
def test_invalid_values_are_reported(changes, problem):
    config = Config()
    for name, value in changes.items():
        setattr(config, name, value)

    assert validate_config(config) == [problem]


def test_saved_config_loads_back_the_same(tmp_path):
    config = Config(slots=["19:00 - 20:00", "18:00 - 19:00"], wake_at="05:50")
    config.next_month_xy = (0.9, 0.12)
    config.labels.continue_ = "Tiếp tục nha"
    path = tmp_path / "CourtBooker" / "config.toml"

    save_config(config, path)

    assert load_config(path) == config
    assert 'continue = "Tiếp tục nha"' in path.read_text(encoding="utf-8")
    assert not (tmp_path / "CourtBooker" / "config.toml.tmp").exists()


def test_saved_config_holds_only_the_changed_labels(tmp_path):
    config = Config()
    path = tmp_path / "config.toml"

    save_config(config, path)
    assert "[labels]" not in path.read_text(encoding="utf-8")

    config.labels.notice = "Thông báo mới"
    save_config(config, path)
    text = path.read_text(encoding="utf-8")
    assert text.endswith('[labels]\nnotice = "Thông báo mới"\n')
    assert load_config(path).labels.home == "Tiện ích"


def test_notification_keys_are_saved_only_when_changed(tmp_path):
    path = tmp_path / "config.toml"

    save_config(Config(), path)
    text = path.read_text(encoding="utf-8")
    # A runner of 0.9.1 refuses keys it does not know, so a default config must not name them.
    assert "windows_notification" not in text
    assert "notification_language" not in text

    save_config(Config(windows_notification=False, notification_language="en"), path)
    text = path.read_text(encoding="utf-8")
    assert "windows_notification = false" in text
    assert 'notification_language = "en"' in text
    assert load_config(path) == Config(windows_notification=False, notification_language="en")


INSTANCE = {"mumu_index": 1, "slots": ["20:00 - 21:00"], "court": "S9 - Sân tennis"}


def test_another_instance_has_its_own_booking_settings(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text(
        'slots = ["18:00 - 19:00"]\ntimeout = 20\n\n[[instances]]\nmumu_index = 1\n'
        'slots = ["20:00 - 21:00"]\ncourt = "S9 - Sân tennis"\n',
        encoding="utf-8",
    )

    config = load_config(path)
    other = instance_config(config, config.instances[0])

    assert config.instances == [INSTANCE]
    assert (other.mumu_index, other.slots, other.court) == (1, ["20:00 - 21:00"], "S9 - Sân tennis")
    assert (other.timeout, other.instances) == (20, [])  # the rest is shared
    assert config.slots == ["18:00 - 19:00"]


def test_the_old_play_day_key_is_dropped(tmp_path):
    # Files of 0.13.1 and before hold days_ahead; the run always books today + 2 now.
    path = tmp_path / "config.toml"
    path.write_text(
        'days_ahead = 1\nslots = ["18:00 - 19:00"]\n\n[[instances]]\nmumu_index = 1\n'
        "days_ahead = 0\n",
        encoding="utf-8",
    )

    config = load_config(path)

    assert config == Config(slots=["18:00 - 19:00"], instances=[{"mumu_index": 1}])
    assert "days_ahead" not in config_to_dict(config)


@pytest.mark.parametrize(
    ("text", "error"),
    [
        ("instances = 1\n", "instances must be [[instances]] tables"),
        ("[[instances]]\nslots = []\n", "Each [[instances]] table needs mumu_index"),
        ("[[instances]]\nmumu_index = 1\ntimeout = 5\n", "Unknown key in [[instances]]: 'timeout'"),
    ],
)
def test_instance_tables_with_unknown_keys_are_refused(tmp_path, text, error):
    path = tmp_path / "config.toml"
    path.write_text(text, encoding="utf-8")

    with pytest.raises(ConfigError, match=re.escape(error)):
        load_config(path)


def test_instances_are_saved_only_when_set(tmp_path):
    path = tmp_path / "config.toml"

    save_config(Config(), path)
    # A runner of 0.12.0 refuses the key: a config with one instance must not name it.
    assert "instances" not in path.read_text(encoding="utf-8")

    save_config(Config(instances=[INSTANCE]), path)
    assert "[[instances]]" in path.read_text(encoding="utf-8")
    assert load_config(path).instances == [INSTANCE]


@pytest.mark.parametrize(
    ("changes", "problem"),
    [
        ({"instances": [{"mumu_index": 0}]}, "MuMu instance 0 is listed twice"),
        ({"instances": [INSTANCE, INSTANCE]}, "MuMu instance 1 is listed twice"),
        ({"instances": [{"mumu_index": -1}]}, "instance mumu_index -1 must be 0 or more"),
        (
            {"instances": [{"mumu_index": 1, "slots": ["8:00"]}]},
            "MuMu instance 1: slot '8:00' must look like '18:00 - 19:00'",
        ),
        (
            {"instances": [INSTANCE], "device": "127.0.0.1:16384"},
            'instances need mumu_manager and device = "auto"',
        ),
    ],
)
def test_invalid_instances_are_reported(changes, problem):
    config = Config()
    for name, value in changes.items():
        setattr(config, name, value)

    assert validate_config(config) == [problem]


def test_a_shared_problem_is_reported_once():
    config = Config(timeout=0, instances=[INSTANCE])

    assert validate_config(config) == ["timeout must be positive"]


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
