"""Simulated booking. Bookings are saved to a JSON file so seats stay taken between runs."""

import json
import random
import re
import string
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

from busbidder.errors import BookingError

# Example: BB-20261116-K7Q2M
BOOKING_REF = re.compile(r"BB-(?P<date>\d{8})-(?P<code>[A-Z0-9]{5})")


@dataclass
class Booking:
    reference: str
    offer_id: str
    traveller: str
    seats: int
    total_eur: float
    changeable: bool
    refundable: bool
    booked_at: str


def load_bookings(path):
    path = Path(path)
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as file:
        data = json.load(file)

    bookings = []
    for item in data:
        if not BOOKING_REF.fullmatch(item["reference"]):
            raise BookingError(f"bad booking reference in {path.name}: {item['reference']}")
        bookings.append(Booking(**item))
    return bookings


def save_bookings(bookings, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as file:
        json.dump([asdict(b) for b in bookings], file, indent=2)


def apply_bookings(offers, bookings):
    """Take seats that were booked in earlier runs away from the offers."""
    by_id = {offer.offer_id: offer for offer in offers}
    for booking in bookings:
        if booking.offer_id in by_id:
            offer = by_id[booking.offer_id]
            offer.seats_available = max(0, offer.seats_available - booking.seats)


def new_reference(existing):
    """Make a reference that is not used by any earlier booking."""
    used = {b.reference for b in existing}
    while True:
        code = "".join(random.choices(string.ascii_uppercase + string.digits, k=5))
        reference = f"BB-{datetime.now():%Y%m%d}-{code}"
        if reference not in used:
            return reference


def book(offer, traveller, seats, bookings):
    """Book seats on an offer. Adds the booking to the list and returns it."""
    traveller = traveller.strip()
    if traveller == "":
        raise BookingError("traveller name is missing")
    if seats < 1:
        raise BookingError("must book at least 1 seat")
    if offer.seats_available < seats:
        raise BookingError(f"only {offer.seats_available} seats left on {offer.offer_id}")

    booking = Booking(
        reference=new_reference(bookings),
        offer_id=offer.offer_id,
        traveller=traveller,
        seats=seats,
        total_eur=round(offer.price_eur * seats, 2),
        changeable=offer.changeable,
        refundable=offer.refundable,
        booked_at=f"{datetime.now():%Y-%m-%d %H:%M}",
    )
    offer.seats_available -= seats
    bookings.append(booking)
    return booking


def confirmation(booking, offer):
    yes_no = {True: "yes", False: "no"}
    return "\n".join([
        f"Booking confirmed: {booking.reference}",
        f"Traveller: {booking.traveller}",
        f"Trip: {offer.company.name}, Madrid to {offer.destination.name}",
        f"Leaves {offer.departure:%d %b %Y %H:%M}, arrives {offer.arrival:%d %b %H:%M}",
        f"Seats: {booking.seats}, total EUR {booking.total_eur:.2f}",
        f"Changeable: {yes_no[booking.changeable]}, refundable: {yes_no[booking.refundable]}",
        f"Seats left on this bus: {offer.seats_available}",
    ])
