class ApplicationError(Exception):
    """General application error"""

    error_code: int
    error: str

    def __init__(self, details: str) -> None:
        self.error = f"{self.error}: {details}"
