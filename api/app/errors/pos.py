"""POS usage errors"""

from app.errors.base import ApplicationError


class POSEntityHasUnpaidInvoices(ApplicationError):
    error_code = 10001
    error = "Entity has unpaid invoices and cannot be charged via POS."
