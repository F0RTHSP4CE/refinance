"""Entity usage errors"""

from refinance.errors.base import ApplicationError


class EntitiesAlreadyPresent(ApplicationError):
    error_code = 4001
    error = "Entities already exist. Can't bootstrap."
