class HomelabAPIError(Exception):
    """Base exception for all Homelab SDK API errors."""
    def __init__(self, message: str, status_code: int = None, response: dict = None):
        super().__init__(message)
        self.status_code = status_code
        self.response = response

class AuthenticationError(HomelabAPIError):
    """Raised when authentication fails (401)."""
    pass

class AuthorizationError(HomelabAPIError):
    """Raised when the user does not have permissions (403)."""
    pass

class NotFoundError(HomelabAPIError):
    """Raised when a resource is not found (404)."""
    pass

class ValidationError(HomelabAPIError):
    """Raised when the API returns a validation error (400, 422)."""
    pass

class ConflictError(HomelabAPIError):
    """Raised when there is a resource conflict (409)."""
    pass

class RateLimitError(HomelabAPIError):
    """Raised when the API rate limit is exceeded (429)."""
    pass

class ServerError(HomelabAPIError):
    """Raised when the API encounters an internal server error (500+)."""
    pass
