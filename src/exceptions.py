class IncodeError(Exception):
    """Base exception for Incode CLI."""
    pass

class LoginError(IncodeError):
    """Raised when authentication fails."""
    pass

class ApiError(IncodeError):
    """Raised when an API request fails."""
    pass

class DataError(IncodeError):
    """Raised when parsing or data validation fails."""
    pass
