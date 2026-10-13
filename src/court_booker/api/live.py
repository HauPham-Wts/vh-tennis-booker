"""The live feed: new activity log steps pushed over a WebSocket as runs write them.

Runs write the history from their own process, so the backend watches the database: it
reads the steps after the last one it sent every :data:`POLL_SECONDS`.
"""

# No `from __future__ import annotations`: FastAPI reads the annotations at run time.
import asyncio
from typing import Any, Optional

from fastapi import APIRouter, WebSocket

from court_booker import history_read
from court_booker.api.context import AppContext

router = APIRouter()

POLL_SECONDS = 0.25
"""How often the database is read for new steps; a step shows within this delay."""


def _read_after(context: AppContext, after: int) -> list[dict[str, Any]]:
    connection = history_read.open_read_only(context.data.database)
    try:
        return history_read.events_after(connection, after)
    finally:
        connection.close()


def _last_id(context: AppContext) -> int:
    connection = history_read.open_read_only(context.data.database)
    try:
        return history_read.last_event_id(connection)
    finally:
        connection.close()


async def _closed(websocket: WebSocket) -> None:
    """Return once the client closes the connection; anything it sends is ignored."""
    while (await websocket.receive())["type"] != "websocket.disconnect":
        pass


@router.websocket("/api/live")
async def live(websocket: WebSocket, after: Optional[int] = None) -> None:
    """Send each new step as ``{"type": "step", "step": {...}}``, oldest first.

    Without ``after`` the feed starts with the next step written; with it, it first sends
    the steps after that one, so a client that reconnects misses nothing.
    """
    context: AppContext = websocket.app.state.context
    # Fixed before accepting, so a step written once the client is connected is sent.
    cursor = after if after is not None else await asyncio.to_thread(_last_id, context)
    await websocket.accept()
    closed = asyncio.ensure_future(_closed(websocket))
    try:
        while not closed.done():
            for step in await asyncio.to_thread(_read_after, context, cursor):
                await websocket.send_json({"type": "step", "step": step})
                cursor = step["id"]
            await asyncio.wait([closed], timeout=POLL_SECONDS)
    finally:
        closed.cancel()
