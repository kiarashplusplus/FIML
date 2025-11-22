"""
Custom exceptions for FIML
"""


class FIMLException(Exception):
    """Base exception for all FIML errors"""

    pass


class ConfigurationError(FIMLException):
    """Configuration-related errors"""

    pass


class ProviderError(FIMLException):
    """Data provider errors"""

    pass


class NoProviderAvailableError(ProviderError):
    """No data provider is available"""

    pass


class RateLimitError(ProviderError):
    """Provider rate limit exceeded"""

    def __init__(self, message: str, retry_after: int = 60):
        super().__init__(message)
        self.retry_after = retry_after


# Alias for backward compatibility
ProviderRateLimitError = RateLimitError


class ProviderTimeoutError(ProviderError):
    """Provider request timeout"""

    pass


class CacheError(FIMLException):
    """Cache-related errors"""

    pass


class ArbitrationError(FIMLException):
    """Data arbitration errors"""

    pass


class ComplianceError(FIMLException):
    """Compliance-related errors"""

    pass


class RegionalRestrictionError(ComplianceError):
    """Access restricted in this region"""

    pass


class FKDSLError(FIMLException):
    """FK-DSL parsing or execution errors"""

    pass


class FKDSLParseError(FKDSLError):
    """FK-DSL syntax error"""

    pass


class FKDSLExecutionError(FKDSLError):
    """FK-DSL execution error"""

    pass


class TaskError(FIMLException):
    """Task execution errors"""

    pass


class TaskNotFoundError(TaskError):
    """Task not found"""

    pass


class TaskTimeoutError(TaskError):
    """Task execution timeout"""

    pass


class ValidationError(FIMLException):
    """Data validation errors"""

    pass


class DataQualityError(FIMLException):
    """Data quality errors"""

    pass


class AuthenticationError(FIMLException):
    """Authentication errors"""

    pass


class AuthorizationError(FIMLException):
    """Authorization errors"""

    pass
