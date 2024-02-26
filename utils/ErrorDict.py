"""
RoWhoIs error dictionary
"""

class DoesNotExistError(Exception):
    """Raised when the requested resource does not exist."""
    pass

class InvalidAuthorizationError(Exception):
    """Raised when authorization for the requested resource is invalid."""
    pass

class UndocumentedError(Exception):
    """Raised when an undocumented error occurs."""
    pass

class MismatchedDataError(Exception):
    """Raised when content was requested using mismatched data."""
    pass

class UnexpectedServerResponseError(Exception):
    """Raised when the server responds with an unexpected status code."""
    pass

class RatelimitedError(Exception):
    """Raised when the requested resource was ratelimited."""
    pass

class AssetNotAvailable(Exception):
    """Raised when the requested asset is not available."""
    pass

class MissingRequiredConfigs(Exception):
    """Raised when configuration options were missing or malformed"""
    pass
