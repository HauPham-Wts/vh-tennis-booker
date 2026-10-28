from court_booker import catalog
from court_booker.config import SPORTS, Config

ORIGAMI_COURTS = {  # the courts of 0.15.0, booked before the catalog
    "tennis": ["S6 - Sân tennis", "S8 - Sân tennis", "S9 - Sân tennis", "S10 - Sân tennis"],
    "pickleball": ["S9 - Sân Pickleball"],
    "badminton": ["S6 - Sân cầu lông", "S8 - Sân Cầu lông", "S10 - Sân cầu lông"],
}


def courts():
    return [
        court
        for subdivision in catalog.SUBDIVISIONS
        for sport in subdivision.sports
        for court in sport.courts
    ]


def test_every_sport_is_one_the_run_books():
    for subdivision in catalog.SUBDIVISIONS:
        ids = [sport.id for sport in subdivision.sports]
        assert set(ids) <= SPORTS.keys(), subdivision.id
        assert len(ids) == len(set(ids)), subdivision.id


def test_origami_keeps_every_sport_and_its_courts():
    origami = catalog.subdivision("origami")

    assert [sport.id for sport in origami.sports] == list(SPORTS)
    for sport, names in ORIGAMI_COURTS.items():
        assert [court.name for court in origami.sport(sport).courts] == names


def test_each_court_is_listed_once_with_a_label():
    names = [court.name for court in courts()]

    assert len(names) == len(set(names))
    assert all(court.label for court in courts())


def test_each_court_names_its_venue():
    assert catalog.venue_of("BE7 - Sân tennis") == "BE _ Sân tennis"
    assert catalog.venue_of("CX2 - Sân tennis 01") == "BS _ Sân tennis"
    assert catalog.venue_of("S10 - Sân tennis") == "Origami_ Sân tennis"
    assert catalog.venue_of("Khu B - Sân tennis") is None


def test_the_default_court_is_in_the_catalog():
    assert catalog.venue_of(Config().court) is not None
    assert catalog.subdivision("khu-b") is None
