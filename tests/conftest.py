"""Shared test helpers."""

from datetime import datetime, timedelta

import pytest

from busbidder.models import Company, Destination, Offer
from busbidder.profiles import Profile

COMPANY = Company("SOL", "SolRuta", "Low-cost")
MALAGA = Destination("MAL", "Malaga", 530, True)


@pytest.fixture
def make_offer():
    """Returns a function that makes an offer. Only the fields a test cares about need to be given."""
    def make(offer_id="SOL-MAL-0712-1", price=30.0, hours=7, leaves="2026-07-12 09:00",
             transfers=0, changeable=False, refundable=False, seats=10, rating=4.0, co2=15.0):
        departure = datetime.strptime(leaves, "%Y-%m-%d %H:%M")
        return Offer(offer_id, COMPANY, MALAGA, departure, departure + timedelta(hours=hours),
                     price, transfers, 20, changeable, refundable, seats, rating, co2)
    return make


@pytest.fixture
def balanced():
    return Profile("balanced", "test", 10,
                   {"price": 0.40, "duration": 0.25, "departure": 0.15, "flexibility": 0.20})
