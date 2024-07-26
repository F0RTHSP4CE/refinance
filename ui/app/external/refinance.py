import requests
from app.config import Config
from app.exceptions.base import ApplicationError
from flask import session


class RefinanceAPI:
    token: str | None = None
    url: str = Config.REFINANCE_API_BASE_URL

    def http(self, method: str, endpoint: str, params=None, data=None):
        try:
            r = requests.request(
                method,
                f"{self.url}/{endpoint}",
                params=params,
                json=data,
                timeout=5,
                headers={"X-Token": self.token},
            )
            if r.status_code != 200:
                e = r.json()
                raise ApplicationError(e)
            return r
        except requests.exceptions.RequestException as e:
            raise ApplicationError(f"Request to API failed: {e}")

    def __init__(self, token: str) -> None:
        self.token = token


def get_refinance_api_client() -> RefinanceAPI:
    token = session.get("token")
    if token is None:
        raise ValueError("Token is required")
    return RefinanceAPI(token)
