from __future__ import annotations

import importlib.util
from decimal import Decimal
from pathlib import Path

MODULE_PATH = Path(__file__).parents[1] / "app" / "invoice_amounts.py"
SPEC = importlib.util.spec_from_file_location("ui_invoice_amounts", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
invoice_display_amounts = MODULE.invoice_display_amounts


def test_simple_invoice_preserves_currency_alternatives() -> None:
    invoice = {
        "amounts": [
            {"currency": "gel", "amount": "115.00"},
            {"currency": "usd", "amount": "42.00"},
        ],
        "items": [],
    }

    assert invoice_display_amounts(invoice) == [
        ("gel", Decimal("115.00")),
        ("usd", Decimal("42.00")),
    ]


def test_multi_recipient_invoice_sums_each_common_currency() -> None:
    invoice = {
        "amounts": [],
        "items": [
            {
                "amounts": [
                    {"currency": "usd", "amount": "42.00"},
                    {"currency": "gel", "amount": "115.00"},
                ]
            },
            {
                "amounts": [
                    {"currency": "usd", "amount": "8.00"},
                    {"currency": "gel", "amount": "20.00"},
                ]
            },
        ],
    }

    assert invoice_display_amounts(invoice) == [
        ("usd", Decimal("50.00")),
        ("gel", Decimal("135.00")),
    ]


def test_multi_recipient_invoice_omits_non_common_currency() -> None:
    invoice = {
        "amounts": [],
        "items": [
            {
                "amounts": [
                    {"currency": "usd", "amount": "42.00"},
                    {"currency": "gel", "amount": "115.00"},
                ]
            },
            {"amounts": [{"currency": "usd", "amount": "8.00"}]},
        ],
    }

    assert invoice_display_amounts(invoice) == [("usd", Decimal("50.00"))]
