"""
RoWhoIs error dictionary
"""


class DoesNotExistError(Exception):
    """Raised when the requested resource does not exist."""


class InvalidAuthorizationError(Exception):
    """Raised when authorization for the requested resource is invalid."""


class UndocumentedError(Exception):
    """Raised when an undocumented error occurs."""


class MismatchedDataError(Exception):
    """Raised when content was requested using mismatched data."""


class UnexpectedServerResponseError(Exception):
    """Raised when the server responds with an unexpected status code."""


class RatelimitedError(Exception):
    """Raised when the requested resource was ratelimited."""


class AssetNotAvailable(Exception):
    """Raised when the requested asset is not available."""


class MissingRequiredConfigs(Exception):
    """Raised when configuration options were missing or malformed"""
