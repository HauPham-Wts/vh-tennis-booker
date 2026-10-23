"""Tests for the notification routes; no notification is shown."""

import pytest

from court_booker import history_read, notify
from court_booker.config import Config, load_config, save_config


class FakeWindows:
    """Stands in for ``notify.send_windows``: records ``(title, body)``, answers ``ok``."""

    def __init__(self):
        self.shown = []
        self.ok = True

    def __call__(self, title, body):
        self.shown.append((title, body))
        return self.ok


@pytest.fixture
def windows(monkeypatch):
    fake = FakeWindows()
    monkeypatch.setattr(notify, "send_windows", fake)
    return fake


def steps(context):
    connection = history_read.open_read_only(context.data.database)
    found = history_read.list_events(connection)
    connection.close()
    return found


def test_notifications_are_on_in_vietnamese_by_default(client, context):
    assert client.get("/api/notifications").json() == {"enabled": True, "language": "vi"}
    assert not context.config_path.exists()  # reading never writes


def test_saved_notification_settings_reach_the_file_and_the_activity_log(client, context):
    save_config(Config(court="S6 - Sân tennis"), context.config_path)

    response = client.put("/api/notifications", json={"enabled": False, "language": "en"})

    assert response.json() == {"enabled": False, "language": "en"}
    written = load_config(context.config_path)
    assert (written.windows_notification, written.notification_language) == (False, "en")
    assert written.court == "S6 - Sân tennis"
    (step,) = steps(context)
    assert step["kind"] == "settings_saved"
    assert step["data"] == {"changed": ["notification_language", "windows_notification"]}


def test_unchanged_notification_settings_write_nothing(client, context):
    response = client.put("/api/notifications", json={"enabled": True, "language": "vi"})

    assert response.status_code == 200
    assert not context.config_path.exists()


def test_settings_keep_the_notification_settings(client, context):
    client.put("/api/notifications", json={"enabled": False, "language": "en"})
    settings = client.get("/api/settings").json()
    settings["court"] = "S9 - Sân tennis"

    client.put("/api/settings", json=settings)

    assert client.get("/api/notifications").json() == {"enabled": False, "language": "en"}


@pytest.mark.parametrize(
    "body",
    [
        {"enabled": True, "language": "fr"},
        {"enabled": True},
        {"enabled": True, "language": "vi", "x": 1},
    ],
)
def test_invalid_notification_settings_are_refused(client, context, body):
    response = client.put("/api/notifications", json=body)

    assert response.status_code == 422
    assert response.json()["error"] == "invalid_request"
    assert not context.config_path.exists()


def test_an_unknown_language_in_the_file_reads_as_vietnamese(client, context):
    context.config_path.write_text('notification_language = "fr"\n', encoding="utf-8")

    assert client.get("/api/notifications").json()["language"] == "vi"


def test_a_test_notification_is_shown_in_the_saved_language(client, context, windows):
    save_config(Config(notification_language="en", windows_notification=False), context.config_path)

    response = client.post("/api/notifications/test")

    assert response.status_code == 204
    assert windows.shown == [
        ("Test notification", "Court Booker will report here after every booking run.")
    ]


def test_a_test_notification_that_fails_answers_503(client, windows):
    windows.ok = False

    response = client.post("/api/notifications/test")

    assert response.status_code == 503
    assert response.json()["error"] == "notification"
