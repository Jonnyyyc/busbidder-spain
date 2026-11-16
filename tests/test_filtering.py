from datetime import date

import pytest

from busbidder.errors import InvalidRequestError
from busbidder.filtering import TravelRequest, filter_offers

JULY_12 = date(2026, 7, 12)


def test_offer_that_fits_is_kept(make_offer):
    kept, removed = filter_offers([make_offer()], TravelRequest("MAL", JULY_12, JULY_12))
    assert len(kept) == 1
    assert sum(removed.values()) == 0


def test_each_rule_removes_an_offer(make_offer):
    offers = [
        make_offer(leaves="2026-07-20 09:00"),
        make_offer(seats=1),
        make_offer(price=80),
        make_offer(transfers=3),
        make_offer(changeable=False),
    ]
    request = TravelRequest("MAL", JULY_12, JULY_12, seats=2, max_price=60,
                            max_transfers=1, needs_changeable=True)
    kept, removed = filter_offers(offers, request)
    assert kept == []
    assert removed["outside travel dates"] == 1
    assert removed["not enough seats"] == 1
    assert removed["over max price"] == 1
    assert removed["too many transfers"] == 1
    assert removed["not changeable"] == 1


def test_boundaries_are_kept(make_offer):
    # Exactly the max price, exactly enough seats, last minute of the last day.
    offer = make_offer(price=60, seats=2, transfers=1, leaves="2026-07-12 23:59")
    request = TravelRequest("MAL", JULY_12, JULY_12, seats=2, max_price=60, max_transfers=1)
    kept, _ = filter_offers([offer], request)
    assert kept == [offer]


def test_sold_out_offer_is_removed(make_offer):
    kept, removed = filter_offers([make_offer(seats=0)], TravelRequest("MAL", JULY_12, JULY_12))
    assert kept == []
    assert removed["not enough seats"] == 1


def test_no_offers_gives_empty_result():
    kept, removed = filter_offers([], TravelRequest("MAL", JULY_12, JULY_12))
    assert kept == []


@pytest.mark.parametrize("changes", [
    dict(destination="XXX"),
    dict(latest=date(2026, 7, 11)),
    dict(seats=0),
    dict(max_price=0),
    dict(max_transfers=-1),
])
def test_bad_requests(changes):
    values = dict(destination="MAL", earliest=JULY_12, latest=JULY_12)
    values.update(changes)
    with pytest.raises(InvalidRequestError):
        TravelRequest(**values).check({"MAL": None})
