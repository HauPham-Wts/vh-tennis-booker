"""Where the app keeps its data: the config, the history database, logs and the run lock.

The installed app uses ``%LOCALAPPDATA%\\CourtBooker``; ``COURT_BOOKER_HOME`` points it
elsewhere, for tests and development. The command line uses this folder for history and
the run lock; its config comes from ``--config`` and relative log paths resolve beside it.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

APP_FOLDER = "CourtBooker"
HOME_ENV = "COURT_BOOKER_HOME"
"""Environment variable that overrides the data folder."""


@dataclass(frozen=True)
class DataFolder:
    """The files of one data folder; nothing is created until :meth:`ensure`."""

    root: Path

    @property
    def config(self) -> Path:
        return self.root / "config.toml"

    @property
    def database(self) -> Path:
        return self.root / "booker.db"

    @property
    def logs(self) -> Path:
        return self.root / "logs"

    @property
    def lock(self) -> Path:
        return self.root / "run.lock"

    def instance_lock(self, index: int) -> Path:
        """Return the run lock of the ``[[instances]]`` entry for MuMu instance ``index``."""
        return self.root / f"run-mumu{index}.lock"

    def ensure(self) -> DataFolder:
        """Create the folder and its log folder if missing, and return it."""
        self.logs.mkdir(parents=True, exist_ok=True)
        return self


def data_folder(environ: Mapping[str, str] = os.environ) -> DataFolder:
    """Return the data folder: ``COURT_BOOKER_HOME``, else ``%LOCALAPPDATA%\\CourtBooker``."""
    override = environ.get(HOME_ENV)
    if override:
        return DataFolder(Path(override))
    local = environ.get("LOCALAPPDATA")
    if local:
        return DataFolder(Path(local) / APP_FOLDER)
    # Outside Windows (CI) there is no LOCALAPPDATA.
    return DataFolder(Path.home() / f".{APP_FOLDER.lower()}")
