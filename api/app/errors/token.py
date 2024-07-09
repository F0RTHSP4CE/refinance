"""Token authentication usage errors"""

from app.errors.base import ApplicationError


class TokenInvalid(ApplicationError):
    http_code = 403
    error_code = 3001
    error = "Token is invalid"


class TokenMissing(ApplicationError):
    http_code = 403
    error_code = 3002
    error = "Token is missing"
