import pytest

from busbidder.errors import InvalidRequestError
from busbidder.profiles import load_profiles
from busbidder.reporting import explain
from busbidder.scoring import CRITERIA, check_weights, normalise, rank_offers


def test_normalise_lower_is_better():
    assert normalise([10, 20, 30], lower_is_better=True) == pytest.approx([100, 50, 0])


def test_normalise_higher_is_better():
    assert normalise([0, 1, 2], lower_is_better=False) == pytest.approx([0, 50, 100])


def test_all_values_the_same_gives_100():
    assert normalise([25, 25, 25], lower_is_better=True) == [100, 100, 100]


def test_single_offer_gets_100():
    assert normalise([42], lower_is_better=True) == [100]


def test_missing_value_gets_0():
    assert normalise([10, None, 20], lower_is_better=True) == [100, 0, 0]


def test_extreme_value_does_not_squeeze_the_rest():
    # Without the clipping, every value from 20 to 39 would score above 98.
    values = list(range(20, 40)) + [1000]
    scores = normalise(values, lower_is_better=True)
    assert scores[0] == 100
    assert scores[-1] == 0
    assert scores[10] < 60


def test_all_criteria_are_registered():
    assert set(CRITERIA) == {"price", "duration", "departure", "flexibility", "rating", "co2"}
    assert CRITERIA["price"].lower_is_better
    assert not CRITERIA["flexibility"].lower_is_better


@pytest.mark.parametrize("weights", [
    {"price": 0.4, "duration": 0.3, "departure": 0.2, "flexibility": 0.2},
    {"price": 0.6, "duration": 0.2, "departure": 0.1, "flexibility": 0.1},
    {"price": 0.5, "duration": 0.5},
    {"price": 0.4, "speed": 0.2, "departure": 0.2, "flexibility": 0.2},
    {"price": -0.1, "duration": 0.5, "departure": 0.3, "flexibility": 0.3},
], ids=["sum above 1", "weight above 0.5", "only 2 criteria", "unknown criterion", "negative"])
def test_bad_weights(weights):
    with pytest.raises(InvalidRequestError):
        check_weights(weights)


def test_weight_limit_is_allowed():
    check_weights({"price": 0.5, "duration": 0.2, "departure": 0.15, "flexibility": 0.15})


def test_cheaper_and_faster_offer_wins(make_offer, balanced):
    good = make_offer("SOL-MAL-0712-1", price=20, hours=6)
    bad = make_offer("SOL-MAL-0712-2", price=40, hours=9)
    ranked = rank_offers([bad, good], balanced)
    assert ranked[0].offer is good


def test_tie_is_broken_by_offer_id(make_offer, balanced):
    a = make_offer("SOL-MAL-0712-1")
    b = make_offer("SOL-MAL-0712-2")
    ranked = rank_offers([b, a], balanced)
    assert ranked[0].total == ranked[1].total
    assert ranked[0].offer is a


def test_scores_stay_between_0_and_100(make_offer, balanced):
    offers = [make_offer(f"SOL-MAL-0712-{i}", price=10 + i * 7, hours=5 + i) for i in range(6)]
    for result in rank_offers(offers, balanced):
        assert 0 <= result.total <= 100
        assert all(0 <= s <= 100 for s in result.scores.values())


def test_explanation_names_strong_and_weak_points(make_offer, balanced):
    cheap_slow = make_offer("SOL-MAL-0712-1", price=20, hours=9)
    dear_fast = make_offer("SOL-MAL-0712-2", price=40, hours=6)
    ranked = rank_offers([cheap_slow, dear_fast], balanced)
    text = explain(ranked[0], balanced)
    assert text.startswith("Strong on price (100)")
    assert "Weakest on duration (0)" in text


def test_profiles_file_is_valid():
    profiles = load_profiles("data/profiles.json")
    assert len(profiles) >= 3


def test_one_offer_has_no_weakest_point(make_offer, balanced):
    ranked = rank_offers([make_offer()], balanced)
    assert "Weakest" not in explain(ranked[0], balanced)


def test_weight_must_be_a_number():
    with pytest.raises(InvalidRequestError):
        check_weights({"price": "0.4", "duration": 0.3, "departure": 0.15, "flexibility": 0.15})


def test_profile_hour_must_be_a_whole_number(tmp_path):
    path = tmp_path / "profiles.json"
    path.write_text('{"x": {"description": "d", "preferred_hour": "10", "weights": '
                    '{"price": 0.4, "duration": 0.25, "departure": 0.15, "flexibility": 0.2}}}')
    with pytest.raises(InvalidRequestError):
        load_profiles(path)
