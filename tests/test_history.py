"""Tests for the history database."""

import sqlite3

import pytest

from court_booker import history


@pytest.fixture
def connection(tmp_path):
    connection = history.connect(tmp_path / "booker.db")
    yield connection
    connection.close()


def tables(connection):
    rows = connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
    return {name for (name,) in rows}


def test_connect_creates_the_tables(tmp_path):
    connection = history.connect(tmp_path / "data" / "booker.db")

    assert tables(connection) == {"runs", "run_slots", "events", "log_lines"}
    assert connection.execute("PRAGMA user_version").fetchone()[0] == history.SCHEMA_VERSION
    assert connection.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
    connection.close()


def test_migrate_twice_changes_nothing(connection):
    assert history.migrate(connection) == history.SCHEMA_VERSION
    assert history.migrate(connection) == history.SCHEMA_VERSION


def test_newer_database_is_left_as_it_is(connection):
    connection.execute(f"PRAGMA user_version = {history.SCHEMA_VERSION + 1}")

    assert history.migrate(connection) == history.SCHEMA_VERSION + 1
    assert tables(connection) == {"runs", "run_slots", "events", "log_lines"}


def test_slots_need_an_existing_run(connection):
    with pytest.raises(sqlite3.IntegrityError):
        connection.execute(
            "INSERT INTO run_slots (run_id, slot, ok, finished_at, seconds, commands)"
            " VALUES (99, '18:00 - 19:00', 1, '2026-10-13T06:00:07', 7.0, 16)"
        )
