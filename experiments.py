"""Runs the experiments used in the evaluation part of the report.

Run with: python experiments.py
"""

from collections import Counter
from datetime import date
from pathlib import Path

from busbidder.filtering import TravelRequest, filter_offers
from busbidder.profiles import Profile, load_profiles
from busbidder.scoring import rank_offers
from busbidder.validation import load_companies, load_destinations, load_offers

DATA = Path(__file__).parent / "data"
FIRST = date(2026, 7, 12)
LAST = date(2026, 7, 14)


def winners_per_profile(offers, destinations, profiles):
    """Which company ranks first for each profile, over all 15 destinations."""
    print("1. Company ranked first, all 15 destinations, 12 to 14 July, no other hard rules")
    for profile in profiles.values():
        wins = Counter()
        night_in_top3 = 0
        for code in destinations:
            kept, _ = filter_offers(offers, TravelRequest(code, FIRST, LAST))
            ranked = rank_offers(kept, profile)
            wins[ranked[0].offer.company.name] += 1
            night_in_top3 += len([r for r in ranked[:3] if r.offer.company.code == "NOC"])
        result = ", ".join(f"{name} {count}" for name, count in wins.most_common())
        print(f"  {profile.name:<9} {result}  (NocheVia in top 3: {night_in_top3} of 15)")
    print()


def price_weight_sweep(offers):
    """The brief request with the price weight changed and the rest kept in the same ratio."""
    print("2. Brief request (MAL, max EUR 50, max 1 transfer, changeable, 08:00), price weight changed")
    request = TravelRequest("MAL", FIRST, LAST, 1, 50, 1, True)
    kept, _ = filter_offers(offers, request)
    for price_weight in [0.1, 0.2, 0.3, 0.4, 0.5]:
        rest = 1 - price_weight
        weights = {"price": price_weight, "duration": rest * 25 / 60,
                   "departure": rest * 15 / 60, "flexibility": rest * 20 / 60}
        ranked = rank_offers(kept, Profile("sweep", "", 8, weights))
        top = ", ".join(f"{r.offer.offer_id} {r.total:.1f}" for r in ranked[:2])
        print(f"  price {price_weight:.0%}: {top}")
    print()


def dataset_summary(offers, companies):
    print("3. Dataset per company")
    print(f"  {'Company':<15} {'Offers':>6} {'Avg EUR':>8} {'Changeable':>10} {'Direct':>7} {'Leaves':>8}")
    for code, company in companies.items():
        own = [o for o in offers if o.company.code == code]
        avg = sum(o.price_eur for o in own) / len(own)
        changeable = len([o for o in own if o.changeable]) / len(own)
        direct = len([o for o in own if o.transfers == 0]) / len(own)
        hours = f"{min(o.departure.hour for o in own)}-{max(o.departure.hour for o in own)}"
        print(f"  {company.name:<15} {len(own):>6} {avg:>8.2f} {changeable:>10.0%} {direct:>7.0%} {hours:>8}")
    print(f"  Sold out: {len([o for o in offers if o.seats_available == 0])}, "
          f"missing CO2: {len([o for o in offers if o.co2_kg is None])}")


def main():
    companies = load_companies(DATA / "companies.csv")
    destinations = load_destinations(DATA / "destinations.csv")
    offers, _ = load_offers(DATA / "offers.csv", companies, destinations)
    profiles = load_profiles(DATA / "profiles.json")

    winners_per_profile(offers, destinations, profiles)
    price_weight_sweep(offers)
    dataset_summary(offers, companies)


if __name__ == "__main__":
    main()
