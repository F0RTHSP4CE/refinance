"""Entity usage errors"""

from app.errors.base import ApplicationError


class DuplicateEntityAuthBinding(ApplicationError):
    http_code = 409
    error_code = 4001
    error = "Entity auth binding already exists"

# not needed anymore, as we have a separate seed/bootstrapping system
#
# class EntitiesAlreadyPresent(ApplicationError):
#     error_code = 4001
#     error = "Entities already exist. Can't bootstrap."
