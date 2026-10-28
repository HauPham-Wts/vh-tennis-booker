"""The subdivisions of Vinhomes Grand Park, and the sports, venues and courts of each.

Each subdivision's account sees its own utilities, venues and courts (field notes,
"Structure of each utility" and "Subdivision BS"). The run needs no subdivision to book: the
court names its venue. The subdivision filters the choices of the app and checks the
settings. Kept free of device access for unit tests; the backend serves it to the UI.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Court:
    """A court as the app names it on its court list, and a short label that tells it apart."""

    name: str
    label: str


@dataclass(frozen=True)
class Venue:
    """A venue as the app names it below "Chọn phân khu", in both of its languages."""

    name: str
    courts: tuple[Court, ...]


@dataclass(frozen=True)
class Sport:
    """A sport of a subdivision, keyed as :data:`court_booker.config.SPORTS` keys it."""

    id: str
    venues: tuple[Venue, ...]

    @property
    def courts(self) -> tuple[Court, ...]:
        """Return the courts of every venue, in the order to offer them."""
        return tuple(court for venue in self.venues for court in venue.courts)


@dataclass(frozen=True)
class Subdivision:
    """A subdivision, with the sports its accounts see, in the order of the app's list."""

    id: str
    name: str
    sports: tuple[Sport, ...]

    def sport(self, sport_id: str) -> Sport | None:
        """Return the sport keyed ``sport_id``, or ``None`` if this subdivision lacks it."""
        return next((sport for sport in self.sports if sport.id == sport_id), None)


def _venue(name: str, *courts: tuple[str, str]) -> Venue:
    return Venue(name, tuple(Court(court, label) for court, label in courts))


SUBDIVISIONS = (
    Subdivision(  # read on 2026-10-27; courts in number order, the first is the default
        "origami",
        "Origami",
        (
            Sport(
                "tennis",
                (
                    _venue(
                        "Origami_ Sân tennis",
                        ("S6 - Sân tennis", "S6"),
                        ("S8 - Sân tennis", "S8"),
                        ("S9 - Sân tennis", "S9"),
                        ("S10 - Sân tennis", "S10"),
                    ),
                ),
            ),
            Sport(
                "multi",
                (
                    _venue(
                        "Origami _ Sân đa năng",
                        ("S7 - Sân đa năng", "S7"),
                        ("S9 - Sân đa năng", "S9"),
                        ("S10 - Sân đa năng", "S10"),
                    ),
                ),
            ),
            Sport(
                "volleyball",
                (
                    _venue(
                        "Origami _ Sân bóng chuyền hơi",
                        ("S8 - Sân bóng chuyền hơi", "S8"),
                        ("S9 - Sân bóng chuyền hơi", "S9"),
                        ("S10 - Sân bóng chuyền hơi 01", "S10 · 01"),
                        ("S10 - Sân bóng chuyền hơi 02", "S10 · 02"),
                    ),
                ),
            ),
            Sport(
                "table-tennis",
                (_venue("Sân bóng bàn", ("S5 - Sân tập bóng bàn 03", "S5")),),
            ),
            Sport(
                "basketball",
                (
                    _venue(
                        "Origami _ Sân bóng rổ",
                        ("S6 - Sân bóng rổ tập ném 01", "S6 · tập ném 01"),
                        ("S6 - Sân bóng rổ tập ném 02", "S6 · tập ném 02"),
                        ("S8 - Sân bóng rổ nửa sân", "S8 · nửa sân"),
                        ("S9 - Sân bóng rổ tập ném 01", "S9 · tập ném 01"),
                        ("S9 - Sân bóng rổ tập ném 02", "S9 · tập ném 02"),
                        ("S10 - Sân bóng rổ nửa sân 03", "S10 · nửa sân 03"),
                        ("S10 - Sân tập bóng rổ 01", "S10 · tập 01"),
                    ),
                ),
            ),
            Sport(
                "football",
                (
                    _venue(
                        "Sân bóng đá",
                        ("S5 - Sân bóng đá 5", "S5 · sân 5"),
                        ("S5 - Sân bóng đá 7", "S5 · sân 7"),
                    ),
                ),
            ),
            Sport(
                "pickleball",
                (_venue("Origami _ Sân Pickleball", ("S9 - Sân Pickleball", "S9")),),
            ),
            Sport(
                "badminton",
                (
                    _venue(
                        "Origami _ Sân cầu lông",
                        ("S6 - Sân cầu lông", "S6"),
                        ("S8 - Sân Cầu lông", "S8"),
                        ("S10 - Sân cầu lông", "S10"),
                    ),
                ),
            ),
        ),
    ),
    Subdivision(  # read on 2026-10-27; its accounts may book the BE venues too
        "bs",
        "BS",
        (
            Sport(
                "volleyball",
                (
                    _venue(
                        "BS _ Sân bóng chuyền hơi",
                        ("BCX3 - Sân bóng chuyền hơi 01", "BCX3 · 01"),
                        ("BCX3 - Sân bóng chuyền hơi 02", "BCX3 · 02"),
                    ),
                ),
            ),
            Sport(
                "tennis",
                (
                    _venue("BE _ Sân tennis", ("BE7 - Sân tennis", "BE7")),
                    _venue(
                        "BS _ Sân tennis",
                        ("BCX3 - Sân tennis 01", "BCX3 · 01"),
                        ("BCX3 - Sân tennis 02", "BCX3 · 02"),
                        ("CX2 - Sân tennis 01", "CX2 · 01"),
                        ("CX2 - Sân tennis 02", "CX2 · 02"),
                    ),
                ),
            ),
            Sport(
                "basketball",
                (
                    _venue(
                        "BE _ Sân bóng rổ",
                        ("BE7 - Sân bóng rổ tập ném 01", "BE7 · tập ném 01"),
                        ("BE7 - Sân bóng rổ tập ném 02", "BE7 · tập ném 02"),
                    ),
                    _venue(
                        "BS _ Sân bóng rổ",
                        ("BCX3 - Sân bóng rổ tập ném 01", "BCX3 · tập ném 01"),
                        ("BCX3 - Sân bóng rổ tập ném 02", "BCX3 · tập ném 02"),
                    ),
                ),
            ),
            Sport(
                "football",
                (_venue("BS _ Sân bóng đá", ("BCX3 - Sân bóng đá", "BCX3")),),
            ),
            Sport(
                "pickleball",
                (
                    _venue("BE _ Sân Pickleball", ("BE7 - Sân Pickleball", "BE7")),
                    _venue(
                        "BS _ Sân Pickleball",
                        ("BCX3 - Sân đa năng (Cầu lông-Pickleball)", "BCX3 · đa năng"),
                    ),
                ),
            ),
            Sport(
                "badminton",
                (_venue("BS _ Sân cầu lông", ("BCX3 - Sân cầu lông 01", "BCX3")),),
            ),
        ),
    ),
)
"""The subdivisions surveyed, Origami first: the default for a court not in the catalog."""

_VENUES = {
    court.name: venue.name
    for subdivision in SUBDIVISIONS
    for sport in subdivision.sports
    for venue in sport.venues
    for court in venue.courts
}


def subdivision(subdivision_id: str) -> Subdivision | None:
    """Return the subdivision keyed ``subdivision_id``, or ``None``."""
    return next((item for item in SUBDIVISIONS if item.id == subdivision_id), None)


def venue_of(court: str) -> str | None:
    """Return the name of the venue that lists ``court``, or ``None`` for a court not here."""
    return _VENUES.get(court)
