"""Custom exceptions for UNMAPPED."""


class UnmappedError(Exception):
    """Base exception for all UNMAPPED errors."""


class ConfigNotFoundError(UnmappedError):
    """Raised when a country config file cannot be located."""


class DataLoadError(UnmappedError):
    """Raised when a required data file fails to load or validate."""


class ExtractionError(UnmappedError):
    """Raised when the LLM skill extraction step fails."""


class MatchingError(UnmappedError):
    """Raised when the opportunity matching step fails."""
