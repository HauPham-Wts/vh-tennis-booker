"""Tests for the device setup checks and auto setup, with fake tools."""

import sys
from pathlib import Path

import pytest

from court_booker import device_setup
from court_booker.device_setup import Status


def install_mumu(folder, layout=("nx_main", "MuMuManager.exe")):
    manager = folder.joinpath(*layout)
    manager.parent.mkdir(parents=True)
    manager.write_bytes(b"")
    return manager


def test_the_configured_manager_comes_first(tmp_path):
    manager = install_mumu(tmp_path / "custom")
    other = install_mumu(tmp_path / "Netease")

    assert device_setup.find_mumu_manager(str(manager), [other.parent.parent]) == manager


def test_the_manager_is_found_in_an_install_folder(tmp_path):
    manager = install_mumu(tmp_path / "MuMuPlayer")

    found = device_setup.find_mumu_manager(
        "C:/missing.exe", [tmp_path / "none", tmp_path / "MuMuPlayer"]
    )

    assert found == manager


def test_an_older_layout_is_found(tmp_path):
    manager = install_mumu(tmp_path / "MuMu Player 12", ("shell", "MuMuManager.exe"))

    assert device_setup.find_mumu_manager("", [tmp_path / "MuMu Player 12"]) == manager


def test_no_mumu_is_found(tmp_path):
    assert device_setup.find_mumu_manager("", [tmp_path]) is None


@pytest.mark.skipif(sys.platform != "win32", reason="the uninstall registry is Windows only")
def test_registry_folders_are_paths():
    assert all(isinstance(folder, Path) for folder in device_setup.installed_folders())


def test_mumu_check(tmp_path):
    manager = install_mumu(tmp_path)

    assert device_setup.check_mumu(None, "").status is Status.USER
    assert device_setup.check_mumu(manager, "").status is Status.FIXABLE
    assert device_setup.check_mumu(manager, "C:/elsewhere.exe").status is Status.FIXABLE
    assert device_setup.check_mumu(manager, str(manager)).status is Status.OK
