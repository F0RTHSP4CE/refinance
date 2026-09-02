"""Fortune-specific application errors."""

from app.errors.base import ApplicationError


class FortuneGameNotFound(ApplicationError):
    http_code = 404
    error_code = 7404
    error = "Fortune game not found"


class InvalidFortunePlay(ApplicationError):
    http_code = 422
    error_code = 7422
    error = "Invalid Fortune play"
