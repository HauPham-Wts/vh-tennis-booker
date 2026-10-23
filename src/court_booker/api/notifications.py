"""Notification routes: the Windows notification after every run, read, saved and tried."""

# No `from __future__ import annotations`: FastAPI and Pydantic read the annotations at run
# time.
from dataclasses import replace
from typing import Literal

from fastapi import APIRouter, Response
from pydantic import BaseModel, ConfigDict

from court_booker import notify
from court_booker.api.activity import record
from court_booker.api.context import Context
from court_booker.api.errors import NotificationError
from court_booker.config import NOTIFICATION_LANGUAGES, Config, save_config
from court_booker.events import EventKind

router = APIRouter(prefix="/api", tags=["notifications"])


class NotificationSettings(BaseModel):
    """Whether every run ends with a Windows notification, and in which language."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool
    language: Literal["vi", "en"]
    """The language of the app's interface, sent by the app when it changes."""


def notification_settings(config: Config) -> NotificationSettings:
    """Return the notification settings of ``config``; an unknown language reads as ``vi``."""
    language = config.notification_language
    return NotificationSettings(
        enabled=config.windows_notification,
        language=language if language in NOTIFICATION_LANGUAGES else notify.DEFAULT_LANGUAGE,
    )


@router.get("/notifications", response_model=NotificationSettings)
def read_notifications(context: Context) -> NotificationSettings:
    """Read the notification settings the next run will use."""
    return notification_settings(context.config())


@router.put("/notifications", response_model=NotificationSettings)
def save_notifications(context: Context, settings: NotificationSettings) -> NotificationSettings:
    """Save the notification settings; they apply from the next run.

    The file is written only when a value changed, and records ``settings_saved`` with the
    changed TOML keys. A config that is invalid otherwise is refused (400 ``bad_request``)
    and left as it was.
    """
    old = context.config()
    config = replace(
        old, windows_notification=settings.enabled, notification_language=settings.language
    )
    changed = [
        key
        for key in ("notification_language", "windows_notification")
        if getattr(config, key) != getattr(old, key)
    ]
    if changed:
        save_config(config, context.config_path)
        record(context, EventKind.SETTINGS_SAVED, changed=changed)
    return notification_settings(config)


@router.post("/notifications/test", status_code=204, response_class=Response)
def test_notification(context: Context) -> Response:
    """Show a sample notification in the saved language, whether notifications are on or not.

    A notification that cannot be shown answers 503 ``notification``.
    """
    title, body = notify.format_test_notification(context.config().notification_language)
    if not notify.send_windows(title, body):
        raise NotificationError("The Windows notification could not be shown; see the log")
    return Response(status_code=204)
