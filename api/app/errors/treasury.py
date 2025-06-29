"""Treasury errors"""

from app.errors.base import ApplicationError


class TreasuryDeletionError(ApplicationError):
    error_code = 8001
    error = "Treasury is used by some Transactions and cannot be deleted"
