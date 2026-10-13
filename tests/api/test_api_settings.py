"""Tests for the settings routes."""

import pytest

from court_booker.config import Config, save_config


@pytest.fixture
def saved(context):
    """Write a config with a Telegram summary and two evening slots, as a user might."""
    config = Config(
        slots=["18:00 - 19:00", "19:00 - 20:00"],
        court="S6 - Sân tennis",
        wake_at="05:50",
        telegram_token="secret-token",
        telegram_chat_id="42",
    )
    save_config(config, context.config_path)
    return config


def test_settings_show_the_config(client, saved):
    settings = client.get("/api/settings").json()

    assert settings["slots"] == ["18:00 - 19:00", "19:00 - 20:00"]
    assert settings["court"] == "S6 - Sân tennis"
    assert settings["labels"]["continue"] == "Tiếp tục"
    assert settings["next_month_xy"] == [0.953, 0.122]


def test_settings_never_show_the_telegram_token(client, saved):
    settings = client.get("/api/settings").json()

    assert "telegram_token" not in settings
    assert "secret-token" not in str(settings)


def test_settings_without_a_config_file_are_the_defaults(client, context):
    assert not context.config_path.exists()

    settings = client.get("/api/settings").json()

    assert settings["days_ahead"] == Config().days_ahead
    assert not context.config_path.exists()  # reading never writes
