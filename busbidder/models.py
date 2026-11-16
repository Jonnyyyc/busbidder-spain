"""Data classes for companies, destinations and offers."""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class Company:
    code: str
    name: str
    profile: str


@dataclass
class Destination:
    code: str
    name: str
    distance_km: int
    coastal: bool


@dataclass
class Offer:
    offer_id: str
    company: Company
    destination: Destination
    departure: datetime
    arrival: datetime
    price_eur: float
    transfers: int
    luggage_kg: int
    changeable: bool
    refundable: bool
    seats_available: int
    rating: float
    co2_kg: float | None  # None if the company did not give a value

    @property
    def duration_minutes(self):
        return int((self.arrival - self.departure).total_seconds() // 60)

    def __str__(self):
        return (f"{self.offer_id} {self.company.name}, {self.departure:%d %b %H:%M}, "
                f"EUR {self.price_eur:.2f}")
