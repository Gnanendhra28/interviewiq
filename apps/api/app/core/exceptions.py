from typing import Any, Optional


class InterviewIQException(Exception):
    def __init__(self, message: str, code: str = "INTERNAL_ERROR", details: Optional[Any] = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details


class DomainException(InterviewIQException):
    def __init__(self, message: str, code: str = "DOMAIN_ERROR", details: Optional[Any] = None):
        super().__init__(message, code=code, details=details)


class UnauthorizedException(InterviewIQException):
    def __init__(self, message: str = "Unauthorized operation", details: Optional[Any] = None):
        super().__init__(message, code="UNAUTHORIZED", details=details)


class ForbiddenException(InterviewIQException):
    def __init__(self, message: str = "Access forbidden", details: Optional[Any] = None):
        super().__init__(message, code="FORBIDDEN", details=details)


class ResourceNotFoundException(InterviewIQException):
    def __init__(self, resource: str, identifier: Any):
        message = f"{resource} with identifier '{identifier}' was not found"
        super().__init__(message, code="NOT_FOUND", details={"resource": resource, "identifier": identifier})


class StateTransitionException(DomainException):
    def __init__(self, current_state: str, action: str):
        message = f"Invalid state transition: Cannot perform action '{action}' while in state '{current_state}'"
        super().__init__(message, code="INVALID_STATE_TRANSITION", details={"current_state": current_state, "action": action})


class AIProviderException(InterviewIQException):
    def __init__(self, message: str, provider: str = "gemini", details: Optional[Any] = None):
        super().__init__(message, code="AI_PROVIDER_ERROR", details={"provider": provider, "extra": details})
