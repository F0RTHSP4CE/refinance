"""Stripe-related application errors."""

from app.errors.base import ApplicationError


class StripeConfigMissing(ApplicationError):
    error_code = 7601
    error = "Stripe is not configured"


class StripeRequestError(ApplicationError):
    error_code = 7602
    error = "Stripe request failed"
    http_code = 422


class StripeWebhookError(ApplicationError):
    error_code = 7603
    error = "Stripe webhook failed"
    http_code = 400
