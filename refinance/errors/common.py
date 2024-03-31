"""Common application errors, may be raised from several services and repositories"""

from refinance.errors.base import ApplicationError


class NotFoundError(ApplicationError):
    error_code = 4040
    error = "Object not found"
