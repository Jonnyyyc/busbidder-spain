"""Hard rules. An offer that breaks one of them is removed before ranking."""

from dataclasses import dataclass
from datetime import date

from busbidder.errors import InvalidRequestError


@dataclass
class TravelRequest:
    destination: str
    earliest: date
    latest: date
    seats: int = 1
    max_price: float | None = None      # per seat
    max_transfers: int | None = None
    needs_changeable: bool = False

    def check(self, destinations):
        if self.destination not in destinations:
            raise InvalidRequestError(f"unknown destination: {self.destination}")
        if self.latest < self.earliest:
            raise InvalidRequestError("latest date is before earliest date")
        if self.seats < 1:
            raise InvalidRequestError("must book at least 1 seat")
        if self.max_price is not None and self.max_price <= 0:
            raise InvalidRequestError("max price must be above 0")
        if self.max_transfers is not None and self.max_transfers < 0:
            raise InvalidRequestError("max transfers cannot be negative")


def filter_offers(offers, request):
    """Returns the offers that pass, and how many were removed by each rule.

    Each offer is counted under the first rule it breaks, so the counts add up
    to the number removed.
    """
    kept = []
    removed = {
        "wrong destination": 0,
        "outside travel dates": 0,
        "not enough seats": 0,
        "over max price": 0,
        "too many transfers": 0,
        "not changeable": 0,
    }

    for offer in offers:
        if offer.destination.code != request.destination:
            removed["wrong destination"] += 1
        elif not request.earliest <= offer.departure.date() <= request.latest:
            removed["outside travel dates"] += 1
        elif offer.seats_available < request.seats:
            removed["not enough seats"] += 1
        elif request.max_price is not None and offer.price_eur > request.max_price:
            removed["over max price"] += 1
        elif request.max_transfers is not None and offer.transfers > request.max_transfers:
            removed["too many transfers"] += 1
        elif request.needs_changeable and not offer.changeable:
            removed["not changeable"] += 1
        else:
            kept.append(offer)

    return kept, removed
