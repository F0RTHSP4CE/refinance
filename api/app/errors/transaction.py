"""Transaction usage errors"""

from app.errors.base import ApplicationError


class CompletedTransactionNotEditable(ApplicationError):
    error_code = 5002
    error = "Can not edit a completed transaction."


class CompletedTransactionNotDeletable(ApplicationError):
    error_code = 5003
    error = "Can not delete a completed transaction."
