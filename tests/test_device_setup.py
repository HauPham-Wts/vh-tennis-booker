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


class FakeMuMu:
    """A MuMu instance with settings, a running state and an installed package list."""

    def __init__(self, settings=None, started=True, packages=("com.vinhomes.resident",)):
        self.values = dict(
            settings
            or {
                "resolution_width": "540.000000",
                "resolution_height": "1600.000000",
                "resolution_dpi": "220.000000",
            }
        )
        self.started = started
        self.packages = packages
        self.changed = []
        self.restarts = 0

    def settings(self, *keys):
        return {key: self.values[key] for key in keys if key in self.values}

    def change_settings(self, values):
        self.changed.append(dict(values))

    def is_started(self):
        return self.started

    def restart(self):
        self.restarts += 1

    def adb_serial(self):
        return "127.0.0.1:16384"


def screen(width, height, dpi):
    return {
        "resolution_width": f"{width}.000000",
        "resolution_height": f"{height}.000000",
        "resolution_dpi": f"{dpi}.000000",
    }


def test_screen_check():
    assert device_setup.check_screen(FakeMuMu()).status is Status.OK
    wrong = device_setup.check_screen(FakeMuMu(screen(540, 960, 240)))
    assert wrong.status is Status.FIXABLE
    assert "540x960 at 240 DPI" in wrong.detail
    assert device_setup.check_screen(None).status is Status.UNKNOWN
    assert device_setup.check_screen(FakeMuMu({"resolution_width": "x"})).status is Status.UNKNOWN


def test_mumu_check(tmp_path):
    manager = install_mumu(tmp_path)

    assert device_setup.check_mumu(None, "").status is Status.USER
    assert device_setup.check_mumu(manager, "").status is Status.FIXABLE
    assert device_setup.check_mumu(manager, "C:/elsewhere.exe").status is Status.FIXABLE
    assert device_setup.check_mumu(manager, str(manager)).status is Status.OK
