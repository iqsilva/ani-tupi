"""Custom exception hierarchy for ani-tupi application.

Provides specific exception types for different failure scenarios,
making error handling more precise and testable.
"""


class AniTupiError(Exception):
    """Base exception for all ani-tupi errors."""

    pass


class PersistenceError(AniTupiError):
    """Raised when JSON file I/O operations fail."""

    pass
