"""Tests for reading the history back."""

import sqlite3

import pytest

from court_booker import history, history_read


def test_a_missing_database_reads_as_empty(tmp_path):
    connection = history_read.open_read_only(tmp_path / "data" / "booker.db")

    assert connection.execute("SELECT COUNT(*) FROM runs").fetchone()[0] == 0
    connection.close()


def test_the_app_cannot_write(tmp_path):
    path = tmp_path / "booker.db"
    history.connect(path).close()
    connection = history_read.open_read_only(path)

    with pytest.raises(sqlite3.OperationalError, match="readonly"):
        connection.execute("DELETE FROM runs")
    connection.close()
