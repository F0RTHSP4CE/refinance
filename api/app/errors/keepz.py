"""Keepz-specific errors."""

from app.errors.base import ApplicationError


class KeepzAuthRequired(ApplicationError):
    error_code = 7401
    error = "Keepz authentication required"


class KeepzAuthFailed(ApplicationError):
    error_code = 7402
    error = "Keepz authentication failed"


class KeepzPaymentLinkMissing(ApplicationError):
    error_code = 7403
    error = "Keepz did not return a payment link"
    http_code = 502
