"""Text output: the ranking table and a short explanation of each result."""

SHORT_NAMES = {"price": "Price", "duration": "Dur", "departure": "Dep",
               "flexibility": "Flex", "rating": "Rate", "co2": "CO2"}


def explain(result, profile):
    """Name up to two criteria the offer is strong on (50 or more) and the one it is weakest on."""
    names = [n for n, w in profile.weights.items() if w > 0]
    names.sort(key=lambda n: result.scores[n], reverse=True)

    strong = [f"{n} ({result.scores[n]:.0f})" for n in names[:2] if result.scores[n] >= 50]
    worst = names[-1]
    if strong:
        text = f"Strong on {' and '.join(strong)}."
    else:
        text = "Not strong on any criterion."
    # With one offer left every score is 100, so there is no weak point to name.
    if result.scores[worst] < 100:
        text += f" Weakest on {worst} ({result.scores[worst]:.0f})."

    offer = result.offer
    if offer.co2_kg is None and "co2" in profile.weights:
        text += " No CO2 value given, so it scored 0 on CO2."
    return text


def format_ranking(results, profile, top=5):
    """Return the top results as a table with the score for each criterion."""
    names = [n for n, w in profile.weights.items() if w > 0]
    header = f"{'#':>2}  {'Offer':<15} {'Company':<15} {'Leaves':<12} {'EUR':>6} {'Hrs':>5} "
    header += " ".join(f"{SHORT_NAMES[n]:>5}" for n in names) + f" {'Total':>6}"
    lines = [header, "-" * len(header)]

    for place, result in enumerate(results[:top], start=1):
        offer = result.offer
        line = (f"{place:>2}  {offer.offer_id:<15} {offer.company.name:<15} "
                f"{offer.departure:%d %b %H:%M} {offer.price_eur:>6.2f} "
                f"{offer.duration_minutes / 60:>5.1f} ")
        line += " ".join(f"{result.scores[n]:>5.0f}" for n in names)
        line += f" {result.total:>6.1f}"
        lines.append(line)
        lines.append(f"    {explain(result, profile)}")
    return "\n".join(lines)
