import pytest

from busbidder.errors import DataFileError, InvalidOfferError
from busbidder.validation import (build_offer, check_offer_id, load_companies,
                                  load_destinations, load_offers, read_csv)

COMPANIES = load_companies("data/companies.csv")
DESTINATIONS = load_destinations("data/destinations.csv")

GOOD_ROW = {
    "offer_id": "SOL-MAL-0712-1", "company": "SOL", "destination": "MAL",
    "departure": "2026-07-12 09:00", "arrival": "2026-07-12 16:30", "price_eur": "29.50",
    "transfers": "1", "luggage_kg": "10", "changeable": "no", "refundable": "no",
    "seats_available": "12", "rating": "3.6", "co2_kg": "16.2",
}


def test_good_row_is_accepted():
    offer = build_offer(GOOD_ROW, COMPANIES, DESTINATIONS)
    assert offer.price_eur == 29.5
    assert offer.duration_minutes == 450


def test_full_dataset_loads_without_rejections():
    offers, rejected = load_offers("data/offers.csv", COMPANIES, DESTINATIONS)
    assert len(offers) == 839
    assert rejected == []


def test_every_planted_error_is_caught():
    offers, rejected = load_offers("data/offers_invalid.csv", COMPANIES, DESTINATIONS)
    assert len(rejected) == 12
    assert len(offers) == 1


@pytest.mark.parametrize("field, value", [
    ("price_eur", "-5"),
    ("price_eur", ""),
    ("price_eur", "cheap"),
    ("departure", "2026-07-32 09:00"),
    ("arrival", "2026-07-12 08:00"),
    ("rating", "5.1"),
    ("seats_available", "-1"),
    ("changeable", "maybe"),
    ("company", "XYZ"),
])
def test_bad_values_are_rejected(field, value):
    row = dict(GOOD_ROW, **{field: value})
    with pytest.raises(InvalidOfferError) as error:
        build_offer(row, COMPANIES, DESTINATIONS)
    assert error.value.field == field


@pytest.mark.parametrize("rating", ["1", "5"])
def test_rating_limits_are_allowed(rating):
    assert build_offer(dict(GOOD_ROW, rating=rating), COMPANIES, DESTINATIONS).rating == float(rating)


def test_zero_seats_is_valid_data():
    assert build_offer(dict(GOOD_ROW, seats_available="0"), COMPANIES, DESTINATIONS).seats_available == 0


def test_missing_co2_becomes_none():
    assert build_offer(dict(GOOD_ROW, co2_kg=""), COMPANIES, DESTINATIONS).co2_kg is None


@pytest.mark.parametrize("offer_id", ["sol-mal-0712-1", "SOL-MAL-712-1", "SOL-MAL-0712-1x", "SOLMAL07121"])
def test_bad_id_format(offer_id):
    with pytest.raises(InvalidOfferError):
        check_offer_id(dict(GOOD_ROW, offer_id=offer_id))


def test_id_must_match_company_and_destination():
    with pytest.raises(InvalidOfferError):
        check_offer_id(dict(GOOD_ROW, offer_id="CAM-MAL-0712-1"))


def test_missing_file():
    with pytest.raises(DataFileError):
        read_csv("data/no_such_file.csv", ["code"])


def test_missing_columns():
    with pytest.raises(DataFileError):
        read_csv("data/companies.csv", ["code", "price"])
