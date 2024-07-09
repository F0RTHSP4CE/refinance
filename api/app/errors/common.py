"""Common application errors, may be raised from several services"""

from app.errors.base import ApplicationError


class NotFoundError(ApplicationError):
    error_code = 1404
    error = "Not found"
