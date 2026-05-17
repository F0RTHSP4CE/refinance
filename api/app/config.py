"""Application configuration"""

import json
from dataclasses import dataclass, field
from os import getenv

DEFAULT_FEE_SELECTION_DEADLINE_DAYS = 30
DEFAULT_SAFETY_CUSHION_ENTITY_ID = 60
DEFAULT_COMMON_CONSUMABLES_ENTITY_ID = 61
DEFAULT_GENERAL_PURCHASE_FUND_ENTITY_ID = 62

DEFAULT_FEE_RULES: list[dict[str, object]] = [
    {
        "membership_tag_id": 2,
        "label": "resident",
        "invoice_amounts": {"usd": "50.00"},
        "legacy_invoice_amounts": {"usd": "42.00"},
        "directed_amounts": {"usd": "4.00"},
        "fixed_allocations": [
            {
                "component_key": "safety_cushion",
                "amounts": {"usd": "2.00"},
                "target_entity_id": DEFAULT_SAFETY_CUSHION_ENTITY_ID,
            },
            {
                "component_key": "common_consumables",
                "amounts": {"usd": "2.00"},
                "target_entity_id": DEFAULT_COMMON_CONSUMABLES_ENTITY_ID,
            },
        ],
        "default_directed_target_entity_id": DEFAULT_GENERAL_PURCHASE_FUND_ENTITY_ID,
    },
    {
        "membership_tag_id": 14,
        "label": "member",
        "invoice_amounts": {"usd": "30.00"},
        "legacy_invoice_amounts": {"usd": "25.00"},
        "directed_amounts": {"usd": "1.00"},
        "fixed_allocations": [
            {
                "component_key": "safety_cushion",
                "amounts": {"usd": "2.00"},
                "target_entity_id": DEFAULT_SAFETY_CUSHION_ENTITY_ID,
            },
            {
                "component_key": "common_consumables",
                "amounts": {"usd": "2.00"},
                "target_entity_id": DEFAULT_COMMON_CONSUMABLES_ENTITY_ID,
            },
        ],
        "default_directed_target_entity_id": DEFAULT_GENERAL_PURCHASE_FUND_ENTITY_ID,
    },
]

DEFAULT_FEE_PRESETS: list[dict[str, str | int]] = [
    {"tag_id": 2, "currency": "usd", "amount": "50.00"},
    {"tag_id": 14, "currency": "usd", "amount": "30.00"},
]


@dataclass
class Config:
    secret_key: str | None = field(default=getenv("REFINANCE_SECRET_KEY", ""))
    pos_secret: str | None = field(default=getenv("REFINANCE_POS_SECRET", ""))
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
    # Optional database URL for Postgres or other databases
    database_url_env: str | None = field(default=getenv("REFINANCE_DATABASE_URL", None))
    fee_presets_raw: str = field(default=getenv("REFINANCE_FEE_PRESETS", ""))
    fee_rules_raw: str = field(default=getenv("REFINANCE_FEE_RULES", ""))
    fee_selection_deadline_days: int = field(
        default=int(
            getenv(
                "REFINANCE_FEE_SELECTION_DEADLINE_DAYS",
                str(DEFAULT_FEE_SELECTION_DEADLINE_DAYS),
            )
        )
    )
    finance_entity_ids_raw: str = field(
        default=getenv("REFINANCE_FINANCE_ENTITY_IDS", "")
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
            presets: list[dict[str, str | int]] = []
            for rule in self.fee_rules:
                tag_id = rule.get("membership_tag_id")
                invoice_amounts = rule.get("invoice_amounts", {})
                if not isinstance(tag_id, int) or not isinstance(invoice_amounts, dict):
                    continue
                for currency, amount in invoice_amounts.items():
                    presets.append(
                        {
                            "tag_id": tag_id,
                            "currency": str(currency).lower(),
                            "amount": str(amount),
                        }
                    )
            return presets or DEFAULT_FEE_PRESETS
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

    @staticmethod
    def _normalize_fee_amounts(raw_value: object) -> dict[str, str]:
        if not isinstance(raw_value, dict):
            return {}
        normalized: dict[str, str] = {}
        for currency, amount in raw_value.items():
            currency_value = str(currency).lower().strip()
            if not currency_value or amount is None:
                continue
            normalized[currency_value] = str(amount)
        return normalized

    def _normalize_fee_rule(self, raw_item: object) -> dict[str, object] | None:
        if not isinstance(raw_item, dict):
            return None
        try:
            membership_tag_id = int(raw_item["membership_tag_id"])
        except (KeyError, TypeError, ValueError):
            return None
        label = str(raw_item.get("label") or f"tag {membership_tag_id}").strip()
        invoice_amounts = self._normalize_fee_amounts(raw_item.get("invoice_amounts"))
        legacy_invoice_amounts = self._normalize_fee_amounts(
            raw_item.get("legacy_invoice_amounts")
        )
        directed_amounts = self._normalize_fee_amounts(raw_item.get("directed_amounts"))
        if not label or not invoice_amounts or not legacy_invoice_amounts:
            return None

        fixed_allocations: list[dict[str, object]] = []
        for item in raw_item.get("fixed_allocations", []):
            if not isinstance(item, dict):
                continue
            component_key = str(item.get("component_key") or "").strip()
            amounts = self._normalize_fee_amounts(item.get("amounts"))
            raw_target_entity_id = item.get("target_entity_id")
            if raw_target_entity_id is None:
                continue
            try:
                target_entity_id = int(raw_target_entity_id)
            except (TypeError, ValueError):
                continue
            if not component_key or not amounts:
                continue
            fixed_allocations.append(
                {
                    "component_key": component_key,
                    "amounts": amounts,
                    "target_entity_id": target_entity_id,
                }
            )

        try:
            default_directed_target_entity_id = int(
                raw_item.get(
                    "default_directed_target_entity_id",
                    DEFAULT_GENERAL_PURCHASE_FUND_ENTITY_ID,
                )
            )
        except (TypeError, ValueError):
            default_directed_target_entity_id = DEFAULT_GENERAL_PURCHASE_FUND_ENTITY_ID

        return {
            "membership_tag_id": membership_tag_id,
            "label": label,
            "invoice_amounts": invoice_amounts,
            "legacy_invoice_amounts": legacy_invoice_amounts,
            "directed_amounts": directed_amounts,
            "fixed_allocations": fixed_allocations,
            "default_directed_target_entity_id": default_directed_target_entity_id,
        }

    @property
    def fee_rules(self) -> list[dict[str, object]]:
        if not self.fee_rules_raw:
            return DEFAULT_FEE_RULES
        try:
            parsed = json.loads(self.fee_rules_raw)
        except json.JSONDecodeError:
            return DEFAULT_FEE_RULES
        if not isinstance(parsed, list):
            return DEFAULT_FEE_RULES
        normalized = [
            rule
            for item in parsed
            if (rule := self._normalize_fee_rule(item)) is not None
        ]
        return normalized or DEFAULT_FEE_RULES

    @property
    def finance_entity_ids(self) -> set[int]:
        entity_ids: set[int] = set()
        for raw_item in self.finance_entity_ids_raw.replace(";", ",").split(","):
            item = raw_item.strip()
            if not item:
                continue
            try:
                entity_ids.add(int(item))
            except ValueError:
                continue
        return entity_ids


def get_config():
    return Config()
