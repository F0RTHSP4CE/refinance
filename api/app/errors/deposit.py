"""Deposit errors"""

from app.errors.base import ApplicationError


class DepositAlreadyCompleted(ApplicationError):
    error_code = 7001
    error = "Deposit is already completed"


class DepositCannotBeEdited(ApplicationError):
    error_code = 7002
    error = "Deposit is not editable anymore"


class DepositAmountIncorrect(ApplicationError):
    error_code = 7003
    error = "Deposit amount is incorrect"
