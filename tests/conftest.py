import logging
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


@pytest.fixture(autouse=True)
def data_home(tmp_path, monkeypatch):
    """Point the data folder at a temporary one, so tests never touch the real history."""
    home = tmp_path / "home"
    monkeypatch.setenv("COURT_BOOKER_HOME", str(home))
    return home


@pytest.fixture(autouse=True)
def restore_package_logger():
    """Undo ``configure_logging`` after each test.

    It turns off propagation on the package logger, which hides records from
    ``caplog`` in later tests (pytest 8 and older).
    """
    logger = logging.getLogger("court_booker")
    saved = (logger.handlers[:], logger.level, logger.propagate)
    yield
    for handler in logger.handlers:
        if handler not in saved[0]:
            handler.close()
    logger.handlers[:], logger.level, logger.propagate = saved
