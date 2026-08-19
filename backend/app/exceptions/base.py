class BaseApplicationException(Exception):
    """Base class for all application exceptions."""
    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)

class ValidationException(BaseApplicationException):
    """Exception raised for validation errors."""
    def __init__(self, message: str, errors: list = None):
        super().__init__(message, status_code=422)
        self.errors = errors or []

class ResourceNotFoundException(BaseApplicationException):
    """Exception raised when a resource is not found."""
    def __init__(self, message: str):
        super().__init__(message, status_code=404)

class DatabaseException(BaseApplicationException):
    """Exception raised for database errors."""
    def __init__(self, message: str):
        super().__init__(message, status_code=500)

class ConflictException(BaseApplicationException):
    """Exception raised for conflicts, e.g., duplicate resources."""
    def __init__(self, message: str):
        super().__init__(message, status_code=409)

class BusinessRuleException(BaseApplicationException):
    """Exception raised for business rule violations."""
    def __init__(self, message: str):
        super().__init__(message, status_code=400)

class WorkflowInvariantError(BaseApplicationException):
    """Exception raised when an impossible workflow state transition occurs."""
    def __init__(self, message: str):
        super().__init__(message, status_code=500)

class ProviderException(BaseApplicationException):
    """Exception raised for LLM provider errors."""
    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message, status_code=status_code)

class RateLimitException(ProviderException):
    def __init__(self, message: str = "Rate limit exceeded"):
        super().__init__(message, status_code=429)

class TimeoutException(ProviderException):
    def __init__(self, message: str = "Request timed out"):
        super().__init__(message, status_code=504)

class InvalidAPIKeyException(ProviderException):
    def __init__(self, message: str = "Invalid API Key"):
        super().__init__(message, status_code=401)

class ModelUnavailableException(ProviderException):
    def __init__(self, message: str = "Model unavailable"):
        super().__init__(message, status_code=503)


class AllProvidersExhaustedException(ProviderException):
    """
    Raised when every configured LLM provider key (across all providers in the
    failover pool) has been exhausted by rate-limits or auth failures.

    This is distinct from a transient RateLimitException on a single provider —
    it signals that no further automatic recovery is possible and the system
    needs human attention (e.g., provide new API keys or wait for quota reset).
    """
    def __init__(self, message: str = "All LLM providers exhausted. Every configured API key has hit its rate limit or is invalid."):
        super().__init__(message, status_code=503)
