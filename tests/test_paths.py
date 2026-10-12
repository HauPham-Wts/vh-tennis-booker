"""Tests for the app's data folder."""

from pathlib import Path

from court_booker.paths import DataFolder, data_folder


def test_override_wins(tmp_path):
    folder = data_folder({"COURT_BOOKER_HOME": str(tmp_path), "LOCALAPPDATA": "C:/ignored"})

    assert folder.root == tmp_path


def test_local_app_data_on_windows():
    folder = data_folder({"LOCALAPPDATA": "C:/Users/me/AppData/Local"})

    assert folder.root == Path("C:/Users/me/AppData/Local") / "CourtBooker"


def test_home_fallback_without_local_app_data():
    assert data_folder({}).root == Path.home() / ".courtbooker"


def test_files_live_in_the_folder(tmp_path):
    folder = DataFolder(tmp_path)

    assert folder.config == tmp_path / "config.toml"
    assert folder.database == tmp_path / "booker.db"
    assert folder.logs == tmp_path / "logs"
    assert folder.lock == tmp_path / "run.lock"


def test_ensure_creates_the_folder_once(tmp_path):
    folder = DataFolder(tmp_path / "CourtBooker")
    assert not folder.root.exists()

    assert folder.ensure() is folder
    folder.ensure()

    assert folder.logs.is_dir()
