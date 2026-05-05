"""Fee allocation errors."""

from app.errors.base import ApplicationError


class FeeAllocationNotFound(ApplicationError):
    error_code = 2404
    error = "Fee allocation not found"


class FeeAllocationSelectionForbidden(ApplicationError):
    http_code = 403
    error_code = 2403
    error = "Fee allocation selection is not allowed"


class FeeAllocationAlreadySettled(ApplicationError):
    error_code = 2409
    error = "Fee allocation was already settled"


class FeeAllocationTargetInvalid(ApplicationError):
    error_code = 2410
    error = "Fee allocation target is invalid"


class FeeRuleNotFound(ApplicationError):
    error_code = 2411
    error = "Fee rule not found"


class FeePolicyForbidden(ApplicationError):
    http_code = 403
    error_code = 2412
    error = "Fee policy access is not allowed"
