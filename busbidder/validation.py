"""Reads the CSV files and checks every offer.

Bad offers are not corrected. They are put aside with a reason, logged, and
written to a file so they can be checked by hand. Loading then carries on.
"""

import csv
import logging
import math
import re
from datetime import datetime
from pathlib import Path

from busbidder.errors import DataFileError, InvalidOfferError
from busbidder.models import Company, Destination, Offer

log = logging.getLogger(__name__)

# Example: SOL-MAL-0712-1 (company, destination, month and day, number)
OFFER_ID = re.compile(r"(?P<company>[A-Z]{3})-(?P<destination>[A-Z]{3})-(?P<date>\d{4})-(?P<number>\d)")

TIME_FORMAT = "%Y-%m-%d %H:%M"

OFFER_COLUMNS = [
    "offer_id", "company", "destination", "departure", "arrival", "price_eur",
    "transfers", "luggage_kg", "changeable", "refundable", "seats_available",
    "rating", "co2_kg",
]


def read_csv(path, columns):
    """Return the rows of a CSV file as a list of dictionaries."""
    path = Path(path)
    try:
        with open(path, newline="", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            rows = list(reader)
            header = reader.fieldnames or []
    except FileNotFoundError:
        raise DataFileError(f"File not found: {path}")

    missing = [c for c in columns if c not in header]
    if missing:
        raise DataFileError(f"{path.name} is missing columns: {', '.join(missing)}")
    return rows


def load_companies(path):
    companies = {}
    for row in read_csv(path, ["code", "name", "profile"]):
        companies[row["code"]] = Company(row["code"], row["name"], row["profile"])
    return companies


def load_destinations(path):
    destinations = {}
    for row in read_csv(path, ["code", "name", "distance_km", "coastal"]):
        destinations[row["code"]] = Destination(
            row["code"], row["name"], int(row["distance_km"]), row["coastal"] == "yes")
    return destinations


def read_number(row, field, kind=float):
    text = row[field]
    if text == "":
        raise InvalidOfferError("missing value", field)
    try:
        number = kind(text)
    except ValueError:
        raise InvalidOfferError(f"not a number: {text}", field)
    # float() also accepts "inf" and "nan"
    if not math.isfinite(number):
        raise InvalidOfferError(f"not a number: {text}", field)
    return number


def read_time(row, field):
    if row[field] == "":
        raise InvalidOfferError("missing value", field)
    try:
        return datetime.strptime(row[field], TIME_FORMAT)
    except ValueError:
        raise InvalidOfferError(f"not a valid date and time: {row[field]}", field)


def read_yes_no(row, field):
    text = row[field].lower()
    if text not in ("yes", "no"):
        raise InvalidOfferError(f"must be yes or no: {row[field]}", field)
    return text == "yes"


def check_offer_id(row):
    """The ID must have the right format and agree with the company and destination columns."""
    match = OFFER_ID.fullmatch(row["offer_id"])
    if not match:
        raise InvalidOfferError(f"wrong ID format: {row['offer_id']}", "offer_id")
    if match.group("company") != row["company"] or match.group("destination") != row["destination"]:
        raise InvalidOfferError("ID does not match company or destination", "offer_id")
    return match.group(0)


def build_offer(row, companies, destinations):
    """Turn one CSV row into an Offer. Raises InvalidOfferError if something is wrong."""
    company = companies.get(row["company"])
    if company is None:
        raise InvalidOfferError(f"unknown company: {row['company']}", "company")

    destination = destinations.get(row["destination"])
    if destination is None:
        raise InvalidOfferError(f"unknown destination: {row['destination']}", "destination")

    offer_id = check_offer_id(row)

    departure = read_time(row, "departure")
    arrival = read_time(row, "arrival")
    if arrival <= departure:
        raise InvalidOfferError("arrival is before departure", "arrival")

    price = read_number(row, "price_eur")
    if price <= 0:
        raise InvalidOfferError(f"price must be above 0: {price}", "price_eur")

    counts = {}
    for field in ("transfers", "luggage_kg", "seats_available"):
        counts[field] = read_number(row, field, int)
        if counts[field] < 0:
            raise InvalidOfferError(f"cannot be negative: {counts[field]}", field)

    rating = read_number(row, "rating")
    if not 1 <= rating <= 5:
        raise InvalidOfferError(f"rating must be between 1 and 5: {rating}", "rating")

    changeable = read_yes_no(row, "changeable")
    refundable = read_yes_no(row, "refundable")

    # CO2 is optional, so an empty value becomes None.
    co2 = None
    if row["co2_kg"] != "":
        co2 = read_number(row, "co2_kg")
        if co2 < 0:
            raise InvalidOfferError(f"cannot be negative: {co2}", "co2_kg")

    return Offer(offer_id, company, destination, departure, arrival, price,
                 counts["transfers"], counts["luggage_kg"], changeable, refundable,
                 counts["seats_available"], rating, co2)


def load_offers(path, companies, destinations):
    """Returns two lists: the good offers and the rejected rows."""
    offers = []
    rejected = []
    seen = set()

    # Row 1 is the header, so the first offer is row 2.
    for row_number, row in enumerate(read_csv(path, OFFER_COLUMNS), start=2):
        # Remove spaces around values. A short row gives None for the missing columns.
        row = {column: (row[column] or "").strip() for column in OFFER_COLUMNS}
        try:
            offer = build_offer(row, companies, destinations)
            if offer.offer_id in seen:
                raise InvalidOfferError(f"duplicate ID: {offer.offer_id}", "offer_id")
        except InvalidOfferError as error:
            rejected.append({"row": row_number, "field": error.field, "reason": str(error), **row})
            log.warning("Row %d rejected (%s): %s", row_number, error.field, error)
            continue

        seen.add(offer.offer_id)
        offers.append(offer)

    sold_out = len([o for o in offers if o.seats_available == 0])
    log.info("Loaded %d offers from %s, %d rejected, %d sold out",
             len(offers), Path(path).name, len(rejected), sold_out)
    return offers, rejected


def save_rejected(rejected, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=["row", "field", "reason"] + OFFER_COLUMNS)
        writer.writeheader()
        writer.writerows(rejected)
