"""Transaction usage errors"""

from refinance.errors.base import ApplicationError


class TransactionAlreadyAdded(ApplicationError):
    error_code = 2001
    error = "Transaction already added"


class TransactionAlreadyRemoved(ApplicationError):
    error_code = 2002
    error = "Transaction already removed"


class TransactionsNotSupported(ApplicationError):
    error_code = 2003
    error = "Transaction functionality is unavailable for this component, but methods are present. WTF?"


class TransactionIsBusy(ApplicationError):
    error_code = 2004
    error = "Transaction is being used by some object(s)"
