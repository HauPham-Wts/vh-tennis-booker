"""What every route works with: the config file and the data folder."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Annotated

from fastapi import Depends, Request

from court_booker.config import Config, load_config
from court_booker.paths import DataFolder


@dataclass(frozen=True)
class AppContext:
    """The files of one backend: the config it edits and the data folder it reads."""

    config_path: Path
    data: DataFolder

    def config(self) -> Config:
        """Read the config as the next run will; it is not cached, so edits show at once."""
        return load_config(self.config_path)


def get_context(request: Request) -> AppContext:
    """Return the context given to ``create_app``."""
    context: AppContext = request.app.state.context
    return context


Context = Annotated[AppContext, Depends(get_context)]
"""Route parameter type that receives the :class:`AppContext`."""
