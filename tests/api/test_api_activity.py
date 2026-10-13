"""Tests for app events recorded by the backend."""

from court_booker import history_read
from court_booker.api.activity import record
from court_booker.api.context import AppContext
from court_booker.events import EventKind
from court_booker.paths import DataFolder


def test_an_app_event_is_recorded_without_a_run(context):
    record(context, EventKind.SETTINGS_SAVED, changed=["slots", "court"])

    connection = history_read.open_read_only(context.data.database)
    (step,) = history_read.list_events(connection)
    connection.close()
    assert (step["run_id"], step["category"], step["kind"]) == (None, "settings", "settings_saved")
    assert step["data"] == {"changed": ["slots", "court"]}


def test_a_database_that_cannot_be_written_is_only_logged(tmp_path, caplog):
    (tmp_path / "home").write_text("not a folder", encoding="utf-8")
    context = AppContext(tmp_path / "config.toml", DataFolder(tmp_path / "home"))

    record(context, EventKind.SETTINGS_SAVED, changed=[])

    assert "Could not record settings_saved in the history" in caplog.text
