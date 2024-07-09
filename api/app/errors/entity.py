"""Entity usage errors"""

from app.errors.base import ApplicationError


class EntitiesAlreadyPresent(ApplicationError):
    error_code = 4001
    error = "Entities already exist. Can't bootstrap."
