from __future__ import annotations

from typing import Any, Mapping


class AppError(Exception):
    def __init__(
        self,
        message: str,
        code: str = "BAD_REQUEST",
        status_code: int = 400,
        details: Mapping[str, Any] | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = dict(details or {})


class NotFoundError(AppError):
    def __init__(self, message: str):
        super().__init__(message, "NOT_FOUND", 404)


class ConflictError(AppError):
    def __init__(self, message: str):
        super().__init__(message, "CONFLICT", 409)


class ValidationError(AppError):
    def __init__(self, message: str, details: Mapping[str, Any] | None = None):
        super().__init__(message, "VALIDATION_ERROR", 422, details)
