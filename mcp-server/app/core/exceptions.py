from enum import Enum
from typing import Any, Dict, Optional, Union


class ErrorCode(str, Enum):
    NOT_FOUND = "NOT_FOUND"
    FORBIDDEN = "FORBIDDEN"
    TIMEOUT = "TIMEOUT"
    VALIDATION_ERROR = "VALIDATION_ERROR"


ErrorCodeValue = Union[ErrorCode, str]


class AppError(Exception):
    def __init__(self, code: ErrorCodeValue, message: str, status_code: int) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


class NotFoundError(AppError):
    def __init__(self, message: str = "Resource not found") -> None:
        super().__init__(ErrorCode.NOT_FOUND, message, 404)


class ForbiddenError(AppError):
    def __init__(self, message: str = "Forbidden") -> None:
        super().__init__(ErrorCode.FORBIDDEN, message, 403)


class ValidationAppError(AppError):
    def __init__(self, message: str = "Validation error") -> None:
        super().__init__(ErrorCode.VALIDATION_ERROR, message, 422)


class TimeoutAppError(AppError):
    def __init__(self, message: str = "Request timed out") -> None:
        super().__init__(ErrorCode.TIMEOUT, message, 504)


def success_response(data: Any) -> Dict[str, Optional[Any]]:
    return {"data": data, "error": None}


def error_response(code: ErrorCodeValue, message: str) -> Dict[str, Any]:
    normalized_code = code.value if isinstance(code, ErrorCode) else str(code)
    return {"data": None, "error": {"code": normalized_code, "message": message}}
