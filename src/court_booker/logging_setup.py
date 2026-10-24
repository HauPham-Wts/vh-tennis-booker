"""Console and file logging with per-step elapsed time."""

from __future__ import annotations

import logging
import sys
import time
from datetime import date
from pathlib import Path

LOGGER_NAME = "court_booker"
_FORMAT = "%(asctime)s.%(msecs)03d +%(elapsed)5.2fs %(levelname)-7s %(message)s"


class _ElapsedFilter(logging.Filter):
    """Attach ``elapsed``: seconds since the previous log record."""

    def __init__(self) -> None:
        super().__init__()
        self._last = time.perf_counter()

    def filter(self, record: logging.LogRecord) -> bool:
        now = time.perf_counter()
        record.elapsed = now - self._last
        self._last = now
        return True


def configure_logging(verbose: bool = False) -> None:
    """Send package logs to stdout as ``HH:MM:SS.mmm +0.00s LEVEL message``.

    The logger itself accepts debug records so that a log file added later gets
    full detail; the console shows them only with ``verbose``. Without a console
    (``pythonw.exe``, where ``sys.stdout`` is ``None``) no console handler is added.
    """
    logger = logging.getLogger(LOGGER_NAME)
    for old in logger.handlers:
        old.close()
    logger.handlers[:] = []
    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    if sys.stdout is None:
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG if verbose else logging.INFO)
    handler.addFilter(_ElapsedFilter())
    handler.setFormatter(logging.Formatter(_FORMAT, datefmt="%H:%M:%S"))
    logger.addHandler(handler)


def add_file_handler(log_dir: Path, today: date | None = None, suffix: str = "") -> Path:
    """Also append full debug logs to ``log_dir/court-booker-YYYY-MM-DD<suffix>.log``."""
    log_dir.mkdir(parents=True, exist_ok=True)
    path = log_dir / f"court-booker-{(today or date.today()).isoformat()}{suffix}.log"
    handler = logging.FileHandler(path, encoding="utf-8")
    handler.setLevel(logging.DEBUG)
    handler.addFilter(_ElapsedFilter())
    handler.setFormatter(logging.Formatter(_FORMAT, datefmt="%Y-%m-%d %H:%M:%S"))
    logging.getLogger(LOGGER_NAME).addHandler(handler)
    return path
