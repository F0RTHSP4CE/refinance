"""Transaction usage errors"""

from app.errors.base import ApplicationError


class TransactionCanNotBeUnconfirmed(ApplicationError):
    error_code = 5001
    error = "You can not un-confirm a confirmed transaction. Create a new one."
