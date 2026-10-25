import logging
import sys
from datetime import date

from court_booker.logging_setup import LOGGER_NAME, add_file_handler, configure_logging


def test_file_gets_debug_and_console_gets_info(tmp_path, capsys):
    configure_logging(verbose=False)
    path = add_file_handler(tmp_path / "logs", today=date(2026, 10, 8))
    logger = logging.getLogger(LOGGER_NAME)

    logger.debug("retrying tap")
    logger.info("Booking confirmed")
    for handler in logger.handlers:
        handler.flush()

    assert path.name == "court-booker-2026-10-08.log"
    text = path.read_text(encoding="utf-8")
    assert "retrying tap" in text
    assert "2026-" in text and "Booking confirmed" in text
    console = capsys.readouterr().out
    assert "Booking confirmed" in console
    assert "retrying tap" not in console
    for handler in logger.handlers:
        handler.close()


def test_another_instance_logs_to_a_file_of_its_own(tmp_path):
    path = add_file_handler(tmp_path / "logs", today=date(2026, 10, 25), suffix="-mumu1")
    for handler in logging.getLogger(LOGGER_NAME).handlers:
        handler.close()

    assert path.name == "court-booker-2026-10-25-mumu1.log"


def test_no_console_handler_without_stdout(monkeypatch):
    monkeypatch.setattr(sys, "stdout", None)
    configure_logging()
    assert logging.getLogger(LOGGER_NAME).handlers == []
