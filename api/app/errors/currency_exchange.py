"""Currency exchange errors"""

from app.errors.base import ApplicationError


class CurrencyExchangeSourceOrTargetAmountZero(ApplicationError):
    error_code = 9001
    error = "Calculated source or target amount is zero. Another amount is likely too small."
