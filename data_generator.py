"""Creates the test data in data/.

Run with: python data_generator.py
The seed is fixed, so the files come out the same every time.
"""

import csv
import random
from datetime import date, datetime, timedelta
from pathlib import Path

SEED = 4420
DATA_DIR = Path(__file__).parent / "data"

# Eight days around the example in the brief (12-14 July).
FIRST_DAY = date(2026, 7, 10)
DAYS = 8

# code, name, rough distance from Madrid in km, coastal
DESTINATIONS = [
    ("BAR", "Barcelona", 620, True),
    ("VAL", "Valencia", 360, True),
    ("SEV", "Seville", 530, False),
    ("MAL", "Malaga", 530, True),
    ("GRA", "Granada", 420, False),
    ("COR", "Cordoba", 400, False),
    ("BIL", "Bilbao", 400, True),
    ("SSB", "San Sebastian", 450, True),
    ("ZAR", "Zaragoza", 320, False),
    ("ALI", "Alicante", 420, True),
    ("MUR", "Murcia", 400, False),
    ("SAL", "Salamanca", 215, False),
    ("TOL", "Toledo", 72, False),
    ("SCQ", "Santiago de Compostela", 600, False),
    ("CAD", "Cadiz", 650, True),
]

# speed in km/h, price per km, share of changeable tickets, luggage kg,
# average rating, CO2 kg per km, and the hours the company departs in.
COMPANIES = {
    "SOL": dict(name="SolRuta", profile="Low-cost daytime services",
                speed=70, per_km=0.055, flex_share=0.2, luggage=10,
                rating=3.6, co2=0.030, hours=(7, 17)),
    "CAM": dict(name="Camino Express", profile="Fast direct connections between major cities",
                speed=85, per_km=0.095, flex_share=0.7, luggage=25,
                rating=4.4, co2=0.030, hours=(6, 20)),
    "COS": dict(name="CostaLink", profile="Strong coverage of coastal destinations",
                speed=72, per_km=0.070, flex_share=0.5, luggage=20,
                rating=4.0, co2=0.028, hours=(8, 18)),
    "VER": dict(name="VerdeBus", profile="Environment-focused services and modern vehicles",
                speed=75, per_km=0.080, flex_share=0.5, luggage=20,
                rating=4.2, co2=0.016, hours=(7, 19)),
    "NOC": dict(name="NocheVia", profile="Overnight and late-evening services",
                speed=62, per_km=0.060, flex_share=0.4, luggage=20,
                rating=3.8, co2=0.027, hours=(21, 24)),
}

TRANSFER_MINUTES = 45

OFFER_COLUMNS = [
    "offer_id", "company", "destination", "departure", "arrival", "price_eur",
    "transfers", "luggage_kg", "changeable", "refundable", "seats_available",
    "rating", "co2_kg",
]


def departures_per_day(code, coastal, rng):
    if code == "SOL":
        return 2
    if code == "COS":
        return 2 if coastal else 1
    if code == "CAM":
        return rng.choice([1, 2])
    return 1


def transfers_for(code, coastal, rng):
    if code == "CAM":
        return 0
    if code == "SOL":
        return rng.choices([0, 1, 2], weights=[5, 4, 1])[0]
    if code == "COS":
        return 0 if coastal else 1
    return rng.choices([0, 1], weights=[7, 3])[0]


def make_offer(code, dest, day, number, rng):
    c = COMPANIES[code]
    dest_code, _, km, coastal = dest

    start, end = c["hours"]
    minute_of_day = rng.randrange(start * 60, end * 60, 30)
    departure = datetime.combine(day, datetime.min.time()) + timedelta(minutes=minute_of_day)

    transfers = transfers_for(code, coastal, rng)
    minutes = km / c["speed"] * 60 + transfers * TRANSFER_MINUTES
    minutes = round(minutes / 5) * 5
    arrival = departure + timedelta(minutes=minutes)

    changeable = rng.random() < c["flex_share"]
    refundable = changeable and rng.random() < 0.5

    price = km * c["per_km"] * rng.uniform(0.85, 1.25)
    if changeable:
        price *= 1.15
    if refundable:
        price *= 1.10
    price = max(price, 6.0)

    # Around 5% are sold out.
    seats = 0 if rng.random() < 0.05 else rng.randint(1, 45)
    rating = min(5.0, max(1.0, c["rating"] + rng.uniform(-0.4, 0.4)))

    # SolRuta sometimes leaves CO2 out, so some values are missing.
    co2 = "" if code == "SOL" and rng.random() < 0.3 else f"{km * c['co2']:.1f}"

    return {
        "offer_id": f"{code}-{dest_code}-{day:%m%d}-{number}",
        "company": code,
        "destination": dest_code,
        "departure": f"{departure:%Y-%m-%d %H:%M}",
        "arrival": f"{arrival:%Y-%m-%d %H:%M}",
        "price_eur": f"{price:.2f}",
        "transfers": transfers,
        "luggage_kg": c["luggage"],
        "changeable": "yes" if changeable else "no",
        "refundable": "yes" if refundable else "no",
        "seats_available": seats,
        "rating": f"{rating:.1f}",
        "co2_kg": co2,
    }


def generate_offers(rng):
    offers = []
    for code in COMPANIES:
        for dest in DESTINATIONS:
            for d in range(DAYS):
                day = FIRST_DAY + timedelta(days=d)
                for number in range(1, departures_per_day(code, dest[3], rng) + 1):
                    offers.append(make_offer(code, dest, day, number, rng))
    return offers


def invalid_offers(valid):
    """Copies of real rows with one error each, plus one good row at the end."""
    rows = [dict(r) for r in valid[:12]]
    rows[0]["price_eur"] = "-12.50"
    rows[1]["destination"] = "XXX"
    rows[2]["departure"] = "2026-07-32 08:00"
    rows[3]["arrival"] = rows[3]["departure"][:11] + "05:00"
    rows[4]["rating"] = "7.2"
    rows[5]["seats_available"] = "-3"
    rows[6]["offer_id"] = "sol_bar_12"
    rows[7]["price_eur"] = ""
    rows[8]["transfers"] = "two"
    rows[9]["company"] = "BUS"
    rows[10]["changeable"] = "maybe"
    rows[11]["offer_id"] = valid[12]["offer_id"]
    rows.append(dict(valid[12]))
    return rows


def write_csv(path, columns, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def main():
    rng = random.Random(SEED)
    DATA_DIR.mkdir(exist_ok=True)

    write_csv(DATA_DIR / "companies.csv", ["code", "name", "profile"],
              [{"code": k, "name": v["name"], "profile": v["profile"]}
               for k, v in COMPANIES.items()])
    write_csv(DATA_DIR / "destinations.csv", ["code", "name", "distance_km", "coastal"],
              [{"code": c, "name": n, "distance_km": km, "coastal": "yes" if coast else "no"}
               for c, n, km, coast in DESTINATIONS])

    offers = generate_offers(rng)
    write_csv(DATA_DIR / "offers.csv", OFFER_COLUMNS, offers)
    write_csv(DATA_DIR / "offers_invalid.csv", OFFER_COLUMNS, invalid_offers(offers))
    print(f"Wrote {len(offers)} offers")


if __name__ == "__main__":
    main()
