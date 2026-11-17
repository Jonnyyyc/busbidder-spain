"""Command line for BusBidder Spain.

Examples:
    python main.py search MAL --from 2026-07-12 --to 2026-07-14 --seats 2 --profile budget
    python main.py compare MAL --from 2026-07-12 --to 2026-07-14
    python main.py book SOL-MAL-0713-1 --name "Ana Garcia" --seats 2
    python main.py validate data/offers_invalid.csv
"""

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

from busbidder.booking import apply_bookings, book, confirmation, load_bookings, save_bookings
from busbidder.errors import BookingError, DataFileError, InvalidRequestError
from busbidder.filtering import TravelRequest, filter_offers
from busbidder.profiles import load_profiles
from busbidder.reporting import format_ranking
from busbidder.scoring import rank_offers
from busbidder.validation import load_companies, load_destinations, load_offers, save_rejected

DATA = Path(__file__).parent / "data"
OUTPUT = Path(__file__).parent / "output"
BOOKINGS = OUTPUT / "bookings.json"


def read_date(text):
    try:
        return datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError:
        raise argparse.ArgumentTypeError(f"date must be YYYY-MM-DD: {text}")


def load_data(offers_file):
    companies = load_companies(DATA / "companies.csv")
    destinations = load_destinations(DATA / "destinations.csv")
    offers, rejected = load_offers(offers_file, companies, destinations)
    if rejected:
        save_rejected(rejected, OUTPUT / "rejected_offers.csv")
    apply_bookings(offers, load_bookings(BOOKINGS))
    return destinations, offers, rejected


def make_request(args, destinations):
    request = TravelRequest(args.destination.upper(), args.date_from, args.date_to, args.seats,
                            args.max_price, args.max_transfers, args.changeable)
    request.check(destinations)
    return request


def show_filter(offers, kept, removed):
    print(f"{len(offers)} offers loaded, {len(kept)} pass the hard rules.")
    for rule, count in removed.items():
        if count:
            print(f"  removed {count:>3}: {rule}")
    print()


def cmd_search(args):
    destinations, offers, _ = load_data(args.offers)
    request = make_request(args, destinations)
    profiles = load_profiles(DATA / "profiles.json")
    if args.profile not in profiles:
        raise InvalidRequestError(f"unknown profile: {args.profile} (choose from {', '.join(profiles)})")
    profile = profiles[args.profile]

    kept, removed = filter_offers(offers, request)
    show_filter(offers, kept, removed)
    if not kept:
        print("No offers left. Try other dates or loosen a hard rule.")
        return

    print(f"Profile: {profile.name} ({profile.description})")
    print("Weights: " + ", ".join(f"{n} {w:.0%}" for n, w in profile.weights.items() if w > 0))
    print()
    print(format_ranking(rank_offers(kept, profile), profile, args.top))


def cmd_compare(args):
    destinations, offers, _ = load_data(args.offers)
    request = make_request(args, destinations)
    kept, removed = filter_offers(offers, request)
    show_filter(offers, kept, removed)
    if not kept:
        print("No offers left. Try other dates or loosen a hard rule.")
        return

    for profile in load_profiles(DATA / "profiles.json").values():
        ranked = rank_offers(kept, profile)
        print(f"{profile.name}:")
        for place, result in enumerate(ranked[:2], start=1):
            print(f"  {place}. {result.offer}  score {result.total:.1f}")


def cmd_book(args):
    _, offers, _ = load_data(args.offers)
    offers_by_id = {offer.offer_id: offer for offer in offers}
    offer = offers_by_id.get(args.offer_id.upper())
    if offer is None:
        raise BookingError(f"no offer with ID {args.offer_id}")

    bookings = load_bookings(BOOKINGS)
    booking = book(offer, args.name, args.seats, bookings)
    save_bookings(bookings, BOOKINGS)
    print(confirmation(booking, offer))


def cmd_validate(args):
    _, offers, rejected = load_data(args.file)
    print(f"{len(offers)} offers accepted, {len(rejected)} rejected.")
    for row in rejected:
        print(f"  row {row['row']:>3}  {row['field']:<16} {row['reason']}")
    if rejected:
        print(f"Rejected rows saved to {OUTPUT / 'rejected_offers.csv'}")


def build_parser():
    parser = argparse.ArgumentParser(description="Find and rank bus offers from Madrid.")
    sub = parser.add_subparsers(dest="command", required=True)

    def add_request_args(p):
        p.add_argument("destination", help="destination code, for example MAL")
        p.add_argument("--from", dest="date_from", type=read_date, required=True, help="earliest date YYYY-MM-DD")
        p.add_argument("--to", dest="date_to", type=read_date, required=True, help="latest date YYYY-MM-DD")
        p.add_argument("--seats", type=int, default=1)
        p.add_argument("--max-price", type=float, help="max price per seat in EUR")
        p.add_argument("--max-transfers", type=int)
        p.add_argument("--changeable", action="store_true", help="only changeable tickets")
        p.add_argument("--offers", default=DATA / "offers.csv")

    search = sub.add_parser("search", help="rank offers for one profile")
    add_request_args(search)
    search.add_argument("--profile", default="balanced")
    search.add_argument("--top", type=int, default=5)
    search.set_defaults(func=cmd_search)

    compare = sub.add_parser("compare", help="show the top 2 offers for every profile")
    add_request_args(compare)
    compare.set_defaults(func=cmd_compare)

    booking = sub.add_parser("book", help="book seats on an offer")
    booking.add_argument("offer_id")
    booking.add_argument("--name", required=True)
    booking.add_argument("--seats", type=int, default=1)
    booking.add_argument("--offers", default=DATA / "offers.csv")
    booking.set_defaults(func=cmd_book)

    validate = sub.add_parser("validate", help="check an offers file and list rejected rows")
    validate.add_argument("file")
    validate.set_defaults(func=cmd_validate)
    return parser


def main():
    args = build_parser().parse_args()

    OUTPUT.mkdir(exist_ok=True)
    logging.basicConfig(filename=OUTPUT / "busbidder.log", level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    try:
        args.func(args)
    except (DataFileError, InvalidRequestError, BookingError) as error:
        logging.error(error)
        print(f"Error: {error}")
        sys.exit(1)


if __name__ == "__main__":
    main()
