"""Invoice usage errors"""

from app.errors.base import ApplicationError


class InvoiceNotEditable(ApplicationError):
    error_code = 8001
    error = "Invoice is not editable anymore."


class InvoiceAlreadyPaid(ApplicationError):
    error_code = 8002
    error = "Invoice is already paid."


class InvoiceTransactionAlreadyAttached(ApplicationError):
    error_code = 8003
    error = "Invoice already has a transaction attached."


class InvoiceEntitiesMismatch(ApplicationError):
    error_code = 8004
    error = "Transaction entities do not match invoice entities."


class InvoiceCurrencyNotAllowed(ApplicationError):
    error_code = 8005
    error = "Transaction currency is not allowed for this invoice."


class InvoiceAmountInsufficient(ApplicationError):
    error_code = 8006
    error = "Transaction amount is insufficient for this invoice."


class InvoiceAmountsRequired(ApplicationError):
    error_code = 8007
    error = "At least one invoice amount must be provided."


class InvoiceTransactionReassignmentNotAllowed(ApplicationError):
    error_code = 8008
    error = "Transaction invoice can not be changed once set."


class InvoiceCancelledNotPayable(ApplicationError):
    error_code = 8009
    error = "Cancelled invoice can not be paid."


class InvoiceAmountInvalid(ApplicationError):
    error_code = 8010
    error = "Invoice amount must be greater than 0."


class InvoiceDuplicateCurrency(ApplicationError):
    error_code = 8011
    error = "Invoice amounts must use unique currencies."
