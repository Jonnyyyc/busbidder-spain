"""Custom exceptions for BusBidder."""


class DataFileError(Exception):
    """Raised when a data file is missing or has the wrong columns."""


class InvalidOfferError(Exception):
    """Raised when a row in the offers file cannot be accepted."""

    def __init__(self, message, field):
        super().__init__(message)
        self.field = field


class InvalidRequestError(Exception):
    """Raised when a travel request or a set of weights is not valid."""


class BookingError(Exception):
    """Raised when a booking cannot be made."""
