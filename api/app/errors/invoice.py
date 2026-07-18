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


class InvoiceInsufficientBalance(ApplicationError):
    error_code = 8012
    error = "Entity does not have sufficient balance to pay this invoice."


class InvoiceIsMultiItem(ApplicationError):
    error_code = 8020
    error = "This invoice has multiple recipients — use POST /invoices/{id}/pay-items."


class InvoiceIsNotMultiItem(ApplicationError):
    error_code = 8021
    error = "This is not a multi-recipient invoice."


class InvoiceItemNotFound(ApplicationError):
    error_code = 8022
    error = "Invoice item not found."


class InvoiceItemEntityRequired(ApplicationError):
    error_code = 8023
    error = "A recipient entity must be specified for this invoice item."


class InvoiceItemInvalidEntityTag(ApplicationError):
    error_code = 8024
    error = "The chosen entity does not have the required tag for this invoice item."


class InvoiceItemCurrencyNotAllowed(ApplicationError):
    error_code = 8025
    error = "The currency is not allowed for this invoice item."


class InvoiceItemAmountInsufficient(ApplicationError):
    error_code = 8026
    error = "The payment amount is insufficient for this invoice item."


class InvoiceItemAlreadyPaid(ApplicationError):
    error_code = 8027
    error = "This invoice item has already been paid."


class InvoicePayItemsMismatch(ApplicationError):
    error_code = 8028
    error = "The provided item IDs do not match the invoice items."


class InvoiceRecipientRotationInvalid(ApplicationError):
    error_code = 8029
    error = "Invoice recipient rotation is missing or invalid."
