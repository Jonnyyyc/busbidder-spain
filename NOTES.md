# Notes

Short log of decisions while building the project. Used later for the README and report.

## Section 0: Setup

New repo `busbidder-spain`. Package folder `busbidder/` with one module per job, `main.py`
to run it, tests with pytest. Standard library only for the program itself.

## Section 1: Design plan

Modules:

| Module | Job |
| --- | --- |
| `errors.py` | custom exceptions |
| `models.py` | Company, Destination, Offer (dataclasses) |
| `validation.py` | read the CSV files and check each offer |
| `filtering.py` | remove offers that break a hard rule |
| `scoring.py` | normalise and weight the criteria, rank offers |
| `booking.py` | make and save a booking |
| `reporting.py` | print rankings and the explanation |
| `main.py` | command line |

Flow: load files -> validate -> filter by hard rules -> score and rank -> show result
-> user picks an offer -> booking saved.

Hard rules (offer removed): destination, travel dates, max price, seats left, max
transfers, changeable ticket if the traveller needs one.

Soft preferences (scored): price, duration, departure time, flexibility. Maybe
transfers and rating as extra criteria.

## Section 2: Dataset

`data_generator.py` makes the data with a fixed seed (4420), so it is the same every run.

- 5 companies, 15 destinations, 8 days (10 to 17 July 2026), 839 offers.
- Each company follows its profile from the brief. NocheVia leaves 21:00 or later,
  Camino Express is always direct and fastest, VerdeBus has the lowest CO2, SolRuta is
  cheapest but has more transfers and mostly non-changeable tickets.
- Distances are rough road distances from Madrid. They are only used so prices and
  durations grow with the length of the trip.
- 54 offers are sold out (0 seats). Some SolRuta offers have no CO2 value on purpose,
  so there is real missing data to deal with.
- `offers_invalid.csv` has 12 rows with one planted error each, plus one good row.

## Section 3: Loading and validation

- Bad rows are rejected, not fixed. Guessing a correct price or date would make up
  data. Rejected rows go to `output/rejected_offers.csv` with the reason, and to the log.
- One bad row does not stop the program. Only a missing file or missing columns stops it.
- Regex is used for the offer ID (`SOL-MAL-0712-1`). Named groups let me check that the
  ID agrees with the company and destination columns.
- Dates are checked with `datetime.strptime`, since a regex would accept 2026-07-32.
- Sold out offers (0 seats) are valid data, so they are kept and logged. They are
  removed in filtering instead.
- CO2 is optional. Blank becomes `None`.
- Result: all 839 offers in `offers.csv` load, and all 12 planted errors in
  `offers_invalid.csv` are caught.
