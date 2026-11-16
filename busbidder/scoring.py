"""Soft preferences. Every offer that passed the hard rules gets a score from 0 to 100.

Each criterion is a small function registered with the @criterion decorator. To add
a new criterion you only write the function, nothing else has to change.
"""

import statistics
from dataclasses import dataclass, field

from busbidder.errors import InvalidRequestError

CRITERIA = {}

# No single criterion may have more than half the total weight.
MAX_WEIGHT = 0.5


def criterion(name, lower_is_better):
    """Register a function that returns the raw value of a criterion for one offer."""
    def decorator(func):
        func.lower_is_better = lower_is_better
        CRITERIA[name] = func
        return func
    return decorator


@criterion("price", lower_is_better=True)
def price(offer, profile):
    return offer.price_eur


@criterion("duration", lower_is_better=True)
def duration(offer, profile):
    return offer.duration_minutes


@criterion("departure", lower_is_better=True)
def departure(offer, profile):
    """Hours away from the time the traveller would like to leave."""
    hour = offer.departure.hour + offer.departure.minute / 60
    return abs(hour - profile.preferred_hour)


@criterion("flexibility", lower_is_better=False)
def flexibility(offer, profile):
    """One point for a changeable ticket, one for a refundable ticket."""
    return int(offer.changeable) + int(offer.refundable)


@criterion("rating", lower_is_better=False)
def rating(offer, profile):
    return offer.rating


@criterion("co2", lower_is_better=True)
def co2(offer, profile):
    return offer.co2_kg  # can be None


def check_weights(weights):
    """Weights must use known criteria, be between 0 and MAX_WEIGHT, and add up to 1."""
    for name, weight in weights.items():
        if name not in CRITERIA:
            raise InvalidRequestError(f"unknown criterion: {name}")
        if not 0 <= weight <= MAX_WEIGHT:
            raise InvalidRequestError(f"weight for {name} must be between 0 and {MAX_WEIGHT}: {weight}")
    if len([w for w in weights.values() if w > 0]) < 4:
        raise InvalidRequestError("at least 4 criteria must have a weight above 0")
    total = sum(weights.values())
    if abs(total - 1) > 0.001:
        raise InvalidRequestError(f"weights must add up to 1, not {total:.3f}")


def normalise(values, lower_is_better):
    """Turn raw values into scores from 0 to 100 within this set of offers.

    Extreme values are pulled in to the 5th and 95th percentile first, so one very
    expensive or very long trip does not squeeze all the other offers together.
    Missing values (None) get 0, so an offer is not rewarded for leaving data out.
    If all values are the same, every offer gets 100.
    """
    known = [v for v in values if v is not None]
    if not known:
        return [0 for _ in values]

    if len(known) >= 2:
        cuts = statistics.quantiles(known, n=20, method="inclusive")
        low, high = cuts[0], cuts[-1]
    else:
        low, high = known[0], known[0]

    scores = []
    for value in values:
        if value is None:
            scores.append(0)
            continue
        if high == low:
            scores.append(100)
            continue
        value = min(max(value, low), high)
        score = (value - low) / (high - low) * 100
        if lower_is_better:
            score = 100 - score
        scores.append(score)
    return scores


@dataclass
class ScoredOffer:
    offer: object
    total: float
    scores: dict = field(default_factory=dict)  # criterion name -> 0 to 100


def rank_offers(offers, profile):
    """Score and sort the offers, best first."""
    check_weights(profile.weights)
    results = [ScoredOffer(offer, 0) for offer in offers]

    for name, weight in profile.weights.items():
        func = CRITERIA[name]
        values = [func(offer, profile) for offer in offers]
        for result, score in zip(results, normalise(values, func.lower_is_better)):
            result.scores[name] = score
            result.total += weight * score

    # Ties: cheaper first, then earlier departure, then offer ID so the order is always the same.
    results.sort(key=lambda r: (-round(r.total, 2), r.offer.price_eur,
                                r.offer.departure, r.offer.offer_id))
    return results
