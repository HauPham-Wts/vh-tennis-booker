"""Tests for the settings routes."""

import pytest

from court_booker import history_read
from court_booker.config import Config, load_config, save_config


@pytest.fixture
def saved(context):
    """Write a config with a Telegram summary and two evening slots, as a user might."""
    config = Config(
        slots=["18:00 - 19:00", "19:00 - 20:00"],
        court="S6 - Sân tennis",
        wake_at="05:50",
        telegram_token="secret-token",
        telegram_chat_id="42",
        notification_language="en",
        instances=[{"mumu_index": 1, "slots": ["20:00 - 21:00"]}],
    )
    save_config(config, context.config_path)
    return config


def test_settings_show_the_config(client, saved):
    settings = client.get("/api/settings").json()

    assert settings["slots"] == ["18:00 - 19:00", "19:00 - 20:00"]
    assert settings["court"] == "S6 - Sân tennis"
    assert settings["labels"]["continue"] == "Tiếp tục"
    assert settings["next_month_xy"] == [0.930, 0.122]


def test_settings_never_show_the_telegram_token(client, saved):
    settings = client.get("/api/settings").json()

    assert "telegram_token" not in settings
    assert "secret-token" not in str(settings)


def test_settings_leave_out_the_notification(client, saved):
    settings = client.get("/api/settings").json()

    assert "windows_notification" not in settings
    assert "notification_language" not in settings


OTHER = {
    "mumu_index": 1,
    "slots": ["20:00 - 21:00"],
    "court": "S6 - Sân tennis",  # from the top of the file
    "venue_keyword": "Origami",
}


def test_settings_show_each_other_instance_in_full(client, saved):
    assert client.get("/api/settings").json()["instances"] == [OTHER]


def test_an_instance_keeps_its_own_settings(client, context, saved):
    settings = client.get("/api/settings").json()
    settings["court"] = "S9 - Sân tennis"
    settings["instances"][0]["slots"] = ["19:00 - 20:00", "20:00 - 21:00"]

    response = client.put("/api/settings", json=settings)

    assert response.status_code == 200
    written = load_config(context.config_path)
    assert written.court == "S9 - Sân tennis"
    assert written.instances == [{**OTHER, "slots": ["19:00 - 20:00", "20:00 - 21:00"]}]
    (step,) = steps(context)
    assert step["data"] == {"changed": ["court", "instances"]}


@pytest.mark.parametrize("instances", [[], [OTHER, {**OTHER, "mumu_index": 2}]])
def test_instances_are_not_added_or_removed_here(client, context, saved, instances):
    settings = client.get("/api/settings").json()
    settings["instances"] = instances
    before = context.config_path.read_bytes()

    response = client.put("/api/settings", json=settings)

    assert response.status_code == 422
    assert response.json()["problems"] == [
        "MuMu instances are added or removed in config.toml, not here"
    ]
    assert context.config_path.read_bytes() == before


def test_settings_without_a_config_file_are_the_defaults(client, context):
    assert not context.config_path.exists()

    settings = client.get("/api/settings").json()

    assert settings["court"] == Config().court
    assert "days_ahead" not in settings
    assert not context.config_path.exists()  # reading never writes


def steps(context):
    connection = history_read.open_read_only(context.data.database)
    found = history_read.list_events(connection)
    connection.close()
    return found


def test_saved_settings_reach_the_file_and_the_activity_log(client, context, saved):
    settings = client.get("/api/settings").json()
    settings["slots"] = ["20:00 - 21:00"]
    settings["court"] = "S9 - Sân tennis"

    response = client.put("/api/settings", json=settings)

    assert response.status_code == 200
    assert response.json()["slots"] == ["20:00 - 21:00"]
    written = load_config(context.config_path)
    assert (written.slots, written.court) == (["20:00 - 21:00"], "S9 - Sân tennis")
    assert written.telegram_token == "secret-token"
    assert written.notification_language == "en"
    assert written.instances == [OTHER]  # now with all its settings
    (step,) = steps(context)
    assert (step["kind"], step["data"]) == ("settings_saved", {"changed": ["court", "slots"]})


def test_labels_are_saved_under_their_toml_names(client, context, saved):
    settings = client.get("/api/settings").json()
    settings["labels"]["continue"] = "Continue"

    client.put("/api/settings", json=settings)

    assert load_config(context.config_path).labels.continue_ == "Continue"


def test_invalid_settings_are_refused_with_each_problem(client, context, saved):
    settings = client.get("/api/settings").json()
    settings["slots"] = ["6pm"]
    settings["wake_at"] = "06:30"
    before = context.config_path.read_bytes()

    response = client.put("/api/settings", json=settings)

    body = response.json()
    assert response.status_code == 422
    assert body["error"] == "invalid_settings"
    assert len(body["problems"]) == 2
    assert context.config_path.read_bytes() == before
    assert steps(context) == []


def test_unknown_settings_are_refused(client, saved):
    settings = client.get("/api/settings").json()
    settings["telegram_token"] = "other"

    response = client.put("/api/settings", json=settings)

    assert response.status_code == 422
    assert response.json()["error"] == "invalid_request"


def test_unchanged_settings_write_nothing(client, context):
    response = client.put("/api/settings", json=client.get("/api/settings").json())

    assert response.status_code == 200
    assert not context.config_path.exists()
    assert steps(context) == []
