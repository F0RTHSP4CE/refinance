"""Transaction usage errors"""

from app.errors.base import ApplicationError


class TransactionCanNotBeEditedAfterConfirmation(ApplicationError):
    error_code = 5002
    error = "Can not edit a confirmed transaction."


class TransactionCanNotBeDeletedAfterConfirmation(ApplicationError):
    error_code = 5003
    error = "Can not delete a confirmed transaction."
