from typing import Any


class ApplicationError(Exception):
    """General application error"""

    http_code: int | None = None
    error_code: int
    error: str

    def __init__(self, details: Any | None = None):
        self.error = self.error
        if details:
            self.error += f": {details}"
