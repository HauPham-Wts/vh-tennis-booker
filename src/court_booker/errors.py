"""Exception hierarchy.

``BookingError`` aborts one booking round and later rounds still run. The other
``CourtBookerError`` subclasses stop the whole run.
"""

from __future__ import annotations

from collections.abc import Iterable


class CourtBookerError(Exception):
    """Base class for all errors raised by court_booker."""


class BookingError(CourtBookerError):
    """Base class for errors that abort a single booking round."""


class ElementNotFoundError(BookingError):
    """A required UI element did not appear within the timeout."""


class NavigationError(BookingError):
    """A tap did not lead to the expected screen."""


class SlotUnavailableError(BookingError):
    """The requested time slot is fully booked."""


class BookingNotOpenError(BookingError):
    """The date or slot did not appear before the retry window ended."""


class BookingRejectedError(BookingError):
    """The app answered the confirmation with a notice instead of the ticket."""


class RequestError(CourtBookerError):
    """Invalid arguments or configuration; nothing was sent to the device."""


class DeviceError(CourtBookerError):
    """The emulator or its ADB connection is not usable."""


class EmulatorError(DeviceError):
    """The emulator could not be found, launched or booted."""


class AdbNotFoundError(DeviceError):
    """No adb executable was found."""


class NoDeviceError(DeviceError):
    """No device is reachable over ADB."""


class MultipleDevicesError(DeviceError):
    """Several devices are reachable and none was chosen."""

    def __init__(self, serials: Iterable[str]) -> None:
        self.serials = list(serials)
        super().__init__(
            f"Several devices found ({', '.join(self.serials)}); set 'device' in config.toml"
        )


class DeviceConnectionError(DeviceError):
    """The configured device could not be connected."""


class AppNotReadyError(CourtBookerError):
    """The app did not reach its home or utilities screen, e.g. after a logout."""


class LockHeldError(CourtBookerError):
    """Another run holds the run lock; nothing was sent to the device."""


class ScheduleError(CourtBookerError):
    """``schtasks`` could not create, delete or query the scheduled task."""
