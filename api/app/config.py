"""Application configuration"""

import json
from dataclasses import dataclass, field
from decimal import Decimal
from os import getenv

DEFAULT_FEE_PRESETS: list[dict[str, str | int]] = [
    {"tag_id": 2, "currency": "usd", "amount": "42"},
    {"tag_id": 2, "currency": "gel", "amount": "115"},
    {"tag_id": 14, "currency": "usd", "amount": "25"},
    {"tag_id": 14, "currency": "gel", "amount": "70"},
]

# Multi-item invoice structure for fee issuance.
# Each entry maps a payer tag_id to an ordered list of invoice items.
# Items may use `to_entity_id` (fixed recipient) or `to_tag_id` (chosen at pay-time).
# Example env var value (JSON):
# [{"tag_id":2,"items":[{"to_entity_id":1,"amounts":[{"currency":"usd","amount":"42"},{"currency":"gel","amount":"115"}]},{"to_tag_id":19,"amounts":[{"currency":"usd","amount":"8"},{"currency":"gel","amount":"20"}]}]},{"tag_id":14,"items":[{"to_entity_id":1,"amounts":[{"currency":"usd","amount":"25"},{"currency":"gel","amount":"65"}]},{"to_tag_id":19,"amounts":[{"currency":"usd","amount":"5"},{"currency":"gel","amount":"15"}]}]}]
DEFAULT_FEE_INVOICE_ITEMS: list[dict] = []


def _env_bool(name: str, default: bool) -> bool:
    value = getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass
class Config:
    secret_key: str | None = field(default=getenv("REFINANCE_SECRET_KEY", ""))
    pos_secret: str | None = field(default=getenv("REFINANCE_POS_SECRET", ""))
    telegram_bot_api_token: str | None = field(
        default=getenv("REFINANCE_TELEGRAM_BOT_API_TOKEN", "")
    )
    telegram_bot_name: str | None = field(
        default=getenv("REFINANCE_TELEGRAM_BOT_NAME", "")
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
    keepz_base_url: str | None = field(
        default=getenv("REFINANCE_KEEPZ_BASE_URL", "https://gateway.keepz.me")
    )
    keepz_user_agent: str | None = field(
        default=getenv(
            "REFINANCE_KEEPZ_USER_AGENT",
            "keepz/10 CFNetwork/3860.300.31 Darwin/25.2.0",
        )
    )
    keepz_poll_interval_seconds: int = field(
        default=int(getenv("REFINANCE_KEEPZ_POLL_INTERVAL_SECONDS", "60"))
    )
    stripe_secret_key: str | None = field(
        default=getenv("REFINANCE_STRIPE_SECRET_KEY", "")
    )
    stripe_webhook_secret: str | None = field(
        default=getenv("REFINANCE_STRIPE_WEBHOOK_SECRET", "")
    )
    stripe_success_url: str | None = field(
        default=getenv("REFINANCE_STRIPE_SUCCESS_URL", "")
    )
    stripe_cancel_url: str | None = field(
        default=getenv("REFINANCE_STRIPE_CANCEL_URL", "")
    )
    stripe_poll_interval_seconds: int = field(
        default=int(getenv("REFINANCE_STRIPE_POLL_INTERVAL_SECONDS", "60"))
    )
    stripe_authorization_max_consecutive_errors: int = field(
        default=int(
            getenv("REFINANCE_STRIPE_AUTHORIZATION_MAX_CONSECUTIVE_ERRORS", "3")
        )
    )
    stripe_entity_charge_enabled: bool = field(
        default=_env_bool("REFINANCE_STRIPE_ENTITY_CHARGE_ENABLED", True)
    )
    stripe_entity_charge_day: int = field(
        default=int(getenv("REFINANCE_STRIPE_ENTITY_CHARGE_DAY", "1"))
    )
    stripe_entity_charge_hour: int = field(
        default=int(getenv("REFINANCE_STRIPE_ENTITY_CHARGE_HOUR", "12"))
    )
    stripe_entity_charge_minute: int = field(
        default=int(getenv("REFINANCE_STRIPE_ENTITY_CHARGE_MINUTE", "0"))
    )
    stripe_guest_charge_enabled: bool = field(
        default=_env_bool("REFINANCE_STRIPE_GUEST_CHARGE_ENABLED", True)
    )
    stripe_guest_charge_hour: int = field(
        default=int(getenv("REFINANCE_STRIPE_GUEST_CHARGE_HOUR", "10"))
    )
    stripe_guest_charge_minute: int = field(
        default=int(getenv("REFINANCE_STRIPE_GUEST_CHARGE_MINUTE", "0"))
    )
    # Optional database URL for Postgres or other databases
    database_url_env: str | None = field(default=getenv("REFINANCE_DATABASE_URL", None))
    fee_presets_raw: str = field(default=getenv("REFINANCE_FEE_PRESETS", ""))
    fee_invoice_items_raw: str = field(
        default=getenv("REFINANCE_FEE_INVOICE_ITEMS", "")
    )
    # Telegram chat/topic to notify on new guest donations
    donation_notification_chat_id: int | None = field(
        default=int(getenv("REFINANCE_DONATION_NOTIFICATION_CHAT_ID") or "0") or None
    )
    donation_notification_topic_id: int | None = field(
        default=int(getenv("REFINANCE_DONATION_NOTIFICATION_TOPIC_ID") or "0") or None
    )
    donation_min_amount: Decimal = field(
        default=Decimal(getenv("REFINANCE_DONATION_MIN_AMOUNT") or "1")
    )
    donation_max_amount: Decimal = field(
        default=Decimal(getenv("REFINANCE_DONATION_MAX_AMOUNT") or "3000")
    )

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

    @property
    def fee_invoice_items(self) -> list[dict]:
        """Per-tag multi-item invoice structure. Returns [] if not configured."""
        if not self.fee_invoice_items_raw:
            return DEFAULT_FEE_INVOICE_ITEMS
        try:
            parsed = json.loads(self.fee_invoice_items_raw)
        except json.JSONDecodeError:
            return DEFAULT_FEE_INVOICE_ITEMS
        if not isinstance(parsed, list):
            return DEFAULT_FEE_INVOICE_ITEMS
        return parsed


def get_config():
    return Config()
