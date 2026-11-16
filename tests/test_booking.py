import json

import pytest

from busbidder.booking import BOOKING_REF, apply_bookings, book, load_bookings, save_bookings
from busbidder.errors import BookingError


def test_booking_lowers_seats(make_offer):
    offer = make_offer(seats=5, price=25)
    bookings = []
    booking = book(offer, "Ana", 2, bookings)
    assert offer.seats_available == 3
    assert booking.total_eur == 50
    assert bookings == [booking]


def test_reference_format(make_offer):
    booking = book(make_offer(), "Ana", 1, [])
    assert BOOKING_REF.fullmatch(booking.reference)


def test_references_are_unique(make_offer):
    offer = make_offer(seats=500)
    bookings = []
    for _ in range(200):
        book(offer, "Ana", 1, bookings)
    assert len({b.reference for b in bookings}) == 200


def test_can_book_the_last_seats(make_offer):
    offer = make_offer(seats=2)
    book(offer, "Ana", 2, [])
    assert offer.seats_available == 0


@pytest.mark.parametrize("name, seats, available", [
    ("Ana", 3, 2),
    ("Ana", 1, 0),
    ("Ana", 0, 5),
    ("  ", 1, 5),
], ids=["not enough seats", "sold out", "zero seats", "no name"])
def test_booking_is_refused(make_offer, name, seats, available):
    offer = make_offer(seats=available)
    with pytest.raises(BookingError):
        book(offer, name, seats, [])
    assert offer.seats_available == available


def test_bookings_are_saved_and_applied(make_offer, tmp_path):
    path = tmp_path / "bookings.json"
    bookings = []
    book(make_offer(seats=10), "Ana", 3, bookings)
    save_bookings(bookings, path)

    fresh = make_offer(seats=10)
    apply_bookings([fresh], load_bookings(path))
    assert fresh.seats_available == 7


def test_bad_reference_in_file(tmp_path):
    path = tmp_path / "bookings.json"
    path.write_text(json.dumps([{
        "reference": "XX-1", "offer_id": "a", "traveller": "b", "seats": 1, "total_eur": 1,
        "changeable": False, "refundable": False, "booked_at": "",
    }]))
    with pytest.raises(BookingError):
        load_bookings(path)


def test_no_bookings_file_gives_empty_list(tmp_path):
    assert load_bookings(tmp_path / "missing.json") == []
