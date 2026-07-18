from decimal import Decimal, InvalidOperation
from os import getenv


def _decimal_env(name: str, default: str) -> Decimal:
    raw_value = getenv(name, default)
    try:
        return Decimal(str(raw_value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{name} must be a decimal amount.") from exc


class Config:
    REFINANCE_API_BASE_URL = getenv("REFINANCE_API_BASE_URL", "http://api:8000")
    TELEGRAM_BOT_NAME = getenv("REFINANCE_TELEGRAM_BOT_NAME", "")
    DONATION_MIN_AMOUNT = _decimal_env("REFINANCE_DONATION_MIN_AMOUNT", "1")
    DONATION_MAX_AMOUNT = _decimal_env("REFINANCE_DONATION_MAX_AMOUNT", "3000")

    if DONATION_MIN_AMOUNT <= 0:
        raise ValueError("REFINANCE_DONATION_MIN_AMOUNT must be greater than 0.")
    if DONATION_MAX_AMOUNT < DONATION_MIN_AMOUNT:
        raise ValueError(
            "REFINANCE_DONATION_MAX_AMOUNT must be greater than or equal to "
            "REFINANCE_DONATION_MIN_AMOUNT."
        )

    UI_CURRENCIES = ["GEL", "USD", "EUR"]
    PREFERRED_CURRENCY = "GEL"
    CURRENCY_CHOICES = [(currency, currency) for currency in UI_CURRENCIES]

    STRIPE_CONFIGURED = bool(getenv("REFINANCE_STRIPE_SECRET_KEY", "").strip())

    FRIDGE_PRESETS = [
        {"amount": 5, "currency": "GEL", "label": "5 GEL"},
        {"amount": 10, "currency": "GEL", "label": "10 GEL"},
        {"amount": 20, "currency": "GEL", "label": "20 GEL"},
        {"amount": 30, "currency": "GEL", "label": "30 GEL"},
    ]
    COFFEE_PRESETS = [
        {"amount": 5, "currency": "GEL", "label": "5 GEL"},
        {"amount": 10, "currency": "GEL", "label": "10 GEL"},
        {"amount": 20, "currency": "GEL", "label": "20 GEL"},
        {"amount": 30, "currency": "GEL", "label": "30 GEL"},
    ]
    TAG_IDS = {
        "fee": 3,
        "deposit": 9,
        "withdrawal": 10,
        "resident": 2,
        "member": 14,
        "room": 19,
    }
    ENTITY_IDS = {
        "f0": 1,
        "fridge": 141,
        "coffee": 150,
    }
