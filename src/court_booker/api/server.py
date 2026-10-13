"""Run the backend: ``court-booker serve``."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from court_booker.api.app import create_app
from court_booker.api.context import AppContext
from court_booker.config import ensure_config, load_config
from court_booker.logging_setup import LOGGER_NAME, add_file_handler, configure_logging
from court_booker.paths import data_folder

logger = logging.getLogger(LOGGER_NAME)

HOST = "127.0.0.1"
"""Only this PC can reach the backend; it has no login."""
DEFAULT_PORT = 8765


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="court-booker serve", description="Run the local backend of the desktop app."
    )
    parser.add_argument(
        "--config", help="config file to edit (default: config.toml in the data folder)"
    )
    parser.add_argument(
        "--port", type=int, default=DEFAULT_PORT, help="port on 127.0.0.1 (default: %(default)s)"
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="show debug output")
    return parser


def main(argv: list[str]) -> int:
    """Serve the backend on 127.0.0.1 until stopped."""
    import uvicorn  # imported here so the tests can replace uvicorn.run

    args = build_parser().parse_args(argv)
    configure_logging(verbose=args.verbose)
    data = data_folder().ensure()
    # The installed app keeps its config in the data folder; development points at the repo.
    config_path = Path(args.config).resolve() if args.config else ensure_config(data.config)
    config = load_config(config_path)
    if config.log_dir:
        logger.debug("Logging to %s", add_file_handler(config_path.parent / config.log_dir))
    logger.info(
        "Backend on http://%s:%d, config %s, data %s", HOST, args.port, config_path, data.root
    )
    uvicorn.run(
        create_app(AppContext(config_path, data)),
        host=HOST,
        port=args.port,
        log_level="info" if args.verbose else "warning",
    )
    return 0
