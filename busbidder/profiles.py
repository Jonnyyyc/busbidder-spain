"""Traveller profiles. A profile is a set of weights and a preferred departure hour."""

import json
from dataclasses import dataclass

from busbidder.errors import DataFileError, InvalidRequestError
from busbidder.scoring import check_weights


@dataclass
class Profile:
    name: str
    description: str
    preferred_hour: int
    weights: dict


def load_profiles(path):
    """Read profiles from a JSON file. Stops with an error if one of them is not valid."""
    try:
        with open(path, encoding="utf-8") as file:
            data = json.load(file)
    except FileNotFoundError:
        raise DataFileError(f"File not found: {path}")
    except json.JSONDecodeError as error:
        raise DataFileError(f"{path} is not valid JSON: {error}")

    profiles = {}
    for name, values in data.items():
        try:
            profile = Profile(name, values["description"], values["preferred_hour"], values["weights"])
        except KeyError as error:
            raise InvalidRequestError(f"profile {name} is missing {error}")
        if not 0 <= profile.preferred_hour <= 23:
            raise InvalidRequestError(f"profile {name}: preferred hour must be 0 to 23")
        try:
            check_weights(profile.weights)
        except InvalidRequestError as error:
            raise InvalidRequestError(f"profile {name}: {error}")
        profiles[name] = profile
    return profiles
