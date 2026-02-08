"""Application configuration"""

import json
from dataclasses import dataclass, field
from os import getenv

DEFAULT_FEE_PRESETS: list[dict[str, str | int]] = [
    {"tag_id": 2, "currency": "usd", "amount": "42"},
    {"tag_id": 2, "currency": "gel", "amount": "115"},
    {"tag_id": 14, "currency": "usd", "amount": "25"},
    {"tag_id": 14, "currency": "gel", "amount": "70"},
]


@dataclass
class Config:
    secret_key: str | None = field(default=getenv("REFINANCE_SECRET_KEY", ""))
    telegram_bot_api_token: str | None = field(
        default=getenv("REFINANCE_TELEGRAM_BOT_API_TOKEN", "")
    )

    ui_url: str | None = field(default=getenv("REFINANCE_UI_URL", ""))
    api_url: str | None = field(default=getenv("REFINANCE_API_URL", ""))

    app_name: str = "refinance"
    app_version: str = "0.1.0"

    cryptapi_address_erc20_usdt: str | None = field(
        default=getenv("REFINANCE_CRYPTAPI_ADDRESS_ERC20_USDT", "")
    )
    cryptapi_address_trc20_usdt: str | None = field(
        default=getenv("REFINANCE_CRYPTAPI_ADDRESS_TRC20_USDT", "")
    )
    # Optional database URL for Postgres or other databases
    database_url_env: str | None = field(default=getenv("REFINANCE_DATABASE_URL", None))
    fee_presets_raw: str = field(default=getenv("REFINANCE_FEE_PRESETS", ""))

    @property
    def database_url(self) -> str:
        # Use provided DATABASE_URL if available, else fall back to Postgres service
        if self.database_url_env:
            return self.database_url_env
        return "postgresql://postgres:postgres@db:5432/refinance"

    @property
    def fee_presets(self) -> list[dict[str, str | int]]:
        if not self.fee_presets_raw:
            return DEFAULT_FEE_PRESETS
        try:
            parsed = json.loads(self.fee_presets_raw)
        except json.JSONDecodeError:
            return DEFAULT_FEE_PRESETS
        if not isinstance(parsed, list):
            return DEFAULT_FEE_PRESETS
        normalized: list[dict[str, str | int]] = []
        for item in parsed:
            if not isinstance(item, dict):
                continue
            tag_id = item.get("tag_id")
            currency = item.get("currency")
            amount = item.get("amount")
            if tag_id is None or currency is None or amount is None:
                continue
            try:
                tag_id_value = int(tag_id)
            except (TypeError, ValueError):
                continue
            currency_value = str(currency).lower().strip()
            if not currency_value:
                continue
            normalized.append(
                {
                    "tag_id": tag_id_value,
                    "currency": currency_value,
                    "amount": str(amount),
                }
            )
        return normalized or DEFAULT_FEE_PRESETS


def get_config():
    return Config()
