import logging

import requests
from app.config import Config
from app.exceptions.base import ApplicationError
from flask import session

logger = logging.getLogger(__name__)


class RefinanceAPI:
    token: str | None = None
    url: str = Config.REFINANCE_API_BASE_URL

    @staticmethod
    def _clean_nested_dicts(d: dict) -> None:
        """Recursively remove csrf_token and submit keys from all nested dicts."""
        for key in list(d.keys()):
            if key in ("csrf_token", "submit"):
                d.pop(key, None)
            else:
                val = d.get(key)
                if isinstance(val, dict):
                    RefinanceAPI._clean_nested_dicts(val)
                elif isinstance(val, list):
                    for item in val:
                        if isinstance(item, dict):
                            RefinanceAPI._clean_nested_dicts(item)

    def http(self, method: str, endpoint: str, params: dict = {}, data: dict = {}):
        # Clean data by removing csrf_token and submit keys recursively
        data = data.copy()
        RefinanceAPI._clean_nested_dicts(data)
        try:
            r = requests.request(
                method,
                f"{self.url}/{endpoint}",
                params=params,
                json=data,
                timeout=5,
                headers={"X-Token": self.token} if self.token else {},
            )
            if r.status_code != 200:
                e = r.json()
                raise ApplicationError(e)
            return r
        except requests.exceptions.RequestException as e:
            raise ApplicationError(f"Request to API failed: {e}")

    def __init__(self, token: str | None) -> None:
        self.token = token


def get_refinance_api_client() -> RefinanceAPI:
    token = session.get("token")
    return RefinanceAPI(token)
