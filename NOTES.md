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
- Spaces around values are removed before checking. A row with too few columns is
  rejected with "missing value" instead of crashing the program.
- `float()` accepts "inf" and "nan", so those are checked for and rejected too.
- Result: all 839 offers in `offers.csv` load, and all 12 planted errors in
  `offers_invalid.csv` are caught.

## Section 4: Filtering (hard rules)

- `TravelRequest` holds what the traveller must have: destination, date range, number
  of seats, and optional max price per seat, max transfers and changeable ticket.
- `check()` stops a request that makes no sense (unknown city, end date before start).
- `filter_offers` returns the kept offers and how many each rule removed. Each offer is
  counted under the first rule it breaks, so the numbers add up and can be shown to the user.
- Example: Malaga, 12 to 14 July, 2 seats, max EUR 60 keeps 14 of 839 offers.

## Section 5: Scoring (soft preferences)

- Criteria: price, duration, departure (hours from the preferred hour), flexibility
  (changeable + refundable), rating, CO2. Each one is a function registered with the
  `@criterion` decorator, which also stores if lower is better. This is the
  metaprogramming part. Adding a criterion means writing one function.
- Each criterion is turned into 0 to 100 within the offers that passed the filter
  (min-max). Lower-is-better criteria are flipped so 100 is always best.
- Extreme values: values are clipped to the 5th and 95th percentile before scaling, so
  one very expensive bus does not push all the others close together.
- Missing CO2 gets 0. I chose this so a company is not rewarded for leaving the value out.
  The explanation tells the user when this happened.
- All values the same: everyone gets 100 on that criterion, so it does not change the order.
- Weights must use known criteria, add up to 1, and at least 4 must be above 0. No weight
  can be above 0.5, so one criterion cannot decide everything on its own.
- Ties: cheaper first, then earlier departure, then offer ID.

## Section 6: Profiles and explanation

- Profiles are in `data/profiles.json`, so they can be changed without touching code.
  Five profiles: balanced (the weights from the brief), budget, business, flexible, eco.
  They are checked when loaded.
- Malaga 12 to 14 July, 2 seats, max EUR 60: balanced and budget pick the cheap SolRuta
  09:30, business, flexible and eco all pick VerdeBus 12:30. Good for the comparison in
  the report.
- Each result gets one line: the two criteria it scored best on and the one it scored worst on.

## Section 7: Booking

- `book()` checks the name and that there are enough seats, then lowers the seat count.
- Reference format `BB-20261116-K7Q2M`, checked with a regex when bookings are loaded.
  A new reference is made until it does not match an earlier one.
- Bookings are saved to `output/bookings.json` with the fare conditions (changeable,
  refundable). On the next run `apply_bookings` takes those seats away again.
- Booking more seats than are left raises `BookingError`.

## Section 8: Command line

- `main.py` uses argparse with four commands: `search`, `compare`, `book`, `validate`.
  I chose separate commands over a menu so every run can be copied into the README and
  the report and gives the same output.
- Errors from my own exceptions are printed as one line and logged, and the program
  exits with code 1. Bad dates are caught by argparse.
- Log file: `output/busbidder.log` (loading summary, every rejected row, errors).

## Section 9: Tests

- 67 tests with pytest, in four files (validation, filtering, scoring, booking).
- Normal cases, invalid values, missing values (empty price, missing CO2, missing file
  and columns) and boundaries (rating 1 and 5, exactly max price, last seat, last
  minute of the last day, weight exactly 0.5, one offer only, all values the same).
- One test failed at first because 50.000000000000014 is not 50. Fixed with pytest.approx.
- When I went over the code again I found that a short row and a broken bookings.json
  crashed the program, and that "inf", "nan" and negative CO2 got through. Fixed, and
  added tests for each.

## Section 10: README and examples

- README has the exact commands. `examples/` has the output from each command, the test
  run and the log file.

## After checking against the brief again

- The brief says the traveller must be able to set the importance of each criterion.
  Added `--weights` so this works without editing `profiles.json`. The weights are
  checked the same way as the profiles.
- Added `--leave-at` for the preferred departure hour ("morning" in the brief example).
- The output now ends with a line saying the top offer is only best for these rules and
  weights, since the brief says not to call it objectively best.
- Explanation changed so "strong on" only lists criteria with 50 or more. Before it could
  say "best on duration (0)" for a weak offer.
- Brief example (MAL, 12 to 14 July, max EUR 50, max 1 transfer, changeable, 08:00):
  5 offers left. Balanced, business, flexible and eco pick CostaLink 14 Jul 10:30.
  Budget picks SolRuta 14 Jul 15:30. That CostaLink bus has only 1 seat left, so after
  one booking it drops out of the next search.
- Eco cannot pick VerdeBus here because every VerdeBus offer is over EUR 50. The hard
  rule decides more than the weights in this case.
- With only 5 offers, min-max is harsh. SolRuta at EUR 30.14 gets 100 on price and the
  CostaLink bus at EUR 44.95 gets 0, even though the gap is about EUR 15.

## Last code check (18 Nov)

- Broken config files (text hour in profiles.json, bad distance, bookings.json that is not a list) now give a normal error instead of a crash.
- `--top` must be at least 1. Before, `--top -1` hid the last offer.
- rejected_offers.csv is always written, so an old one is not left behind.
- With one offer left, the explanation no longer names a "weakest" criterion that scored 100.
- The validate command prints the short path to the rejected file.
- 74 tests now.
