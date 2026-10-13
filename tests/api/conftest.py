"""Backend tests: skipped without the ``app`` extra (FastAPI)."""

import importlib.util

collect_ignore_glob = [] if importlib.util.find_spec("fastapi") else ["test_*.py"]
