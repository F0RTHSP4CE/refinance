from refinance.errors.base import ApplicationError


class NotFoundError(ApplicationError):
    error_code = 4040
    error = "Object not found"
