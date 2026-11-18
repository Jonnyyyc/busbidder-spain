# BusBidder Spain

Final project in ACIT4420 Problem-Solving with Scripting (OsloMet, autumn 2026).

A command line program that takes bus offers from Madrid to 15 Spanish cities, removes
the offers that break the traveller's hard rules, ranks the rest with a weighted score,
explains the result, and makes a simulated booking.

## Requirements

- Python 3.10 or newer (tested with Python 3.14.3)
- The program only uses the standard library. pytest is needed for the tests.

```
python -m pip install -r requirements.txt
```

## How to run

All commands are run from the project folder.

Rank offers for one profile:

```
python main.py search MAL --from 2026-07-12 --to 2026-07-14 --seats 2 --max-price 60 --profile budget
```

The example request from the brief (Malaga, 12 to 14 July, max EUR 50, max 1 transfer,
changeable ticket, morning departure):

```
python main.py search MAL --from 2026-07-12 --to 2026-07-14 --max-price 50 --max-transfers 1 --changeable --leave-at 8
```

Use your own weights instead of a profile:

```
python main.py search MAL --from 2026-07-12 --to 2026-07-14 --weights price=0.4,duration=0.25,departure=0.15,flexibility=0.2
```

Show the top 2 offers for every profile:

```
python main.py compare MAL --from 2026-07-12 --to 2026-07-14 --seats 2 --max-price 60
```

Book an offer:

```
python main.py book COS-MAL-0714-2 --name "Ana Garcia"
```

Check a data file and list the rows that were rejected:

```
python main.py validate data/offers_invalid.csv
```

Run the tests:

```
python -m pytest
```

Run the experiments used in the report:

```
python experiments.py
```

Make the data again (gives the same files every time):

```
python data_generator.py
```

`python main.py --help` and `python main.py search --help` list all options.

### Search options

| Option | Meaning |
| --- | --- |
| `MAL` | destination code, see `data/destinations.csv` |
| `--from`, `--to` | first and last day the traveller can leave (YYYY-MM-DD) |
| `--seats` | number of seats, default 1 |
| `--max-price` | max price per seat in EUR |
| `--max-transfers` | max number of transfers |
| `--changeable` | only show changeable tickets |
| `--profile` | balanced, budget, business, flexible or eco |
| `--weights` | own weights, for example `price=0.4,duration=0.25,departure=0.15,flexibility=0.2` |
| `--leave-at` | preferred departure hour (0 to 23), replaces the one in the profile |
| `--top` | how many results to show, default 5 |

The data covers 10 to 17 July 2026.

## Files

```
main.py                 command line
data_generator.py       makes the data in data/
experiments.py          runs the experiments in the report
busbidder/
    errors.py           custom exceptions
    models.py           Company, Destination, Offer
    validation.py       reads and checks the CSV files
    filtering.py        hard rules
    scoring.py          criteria, normalisation, weights, ranking
    profiles.py         loads traveller profiles
    reporting.py        ranking table and explanation
    booking.py          booking and booking references
data/
    companies.csv, destinations.csv, offers.csv
    offers_invalid.csv  rows with planted errors, used to test validation
    profiles.json       weights for each traveller profile
tests/                  pytest tests
examples/               saved output used in the report
NOTES.md                decisions made while building the project
```

The program writes to `output/`: the log file `busbidder.log`, rejected rows in
`rejected_offers.csv`, and bookings in `bookings.json`. Delete `output/bookings.json`
to reset the seats.

## How the ranking works

1. Offers are removed if they break a hard rule: wrong destination, outside the dates,
   not enough seats, over the max price, too many transfers, or not changeable when the
   traveller needs it.
2. Each remaining offer gets a score from 0 to 100 for every criterion in the profile
   (price, duration, departure time, flexibility, rating, CO2). The scale is set by the
   offers that are left, and lower-is-better criteria are flipped so 100 is always best.
3. The total is the weighted sum. Weights must add up to 1 and no weight can be above 0.5.

More detail is in `NOTES.md` and in the report.
