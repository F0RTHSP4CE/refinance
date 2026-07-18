from __future__ import annotations

from decimal import Decimal
from typing import Any


def _value(obj: Any, name: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _amount_map(amounts: list[Any]) -> tuple[list[str], dict[str, Decimal]]:
    order: list[str] = []
    values: dict[str, Decimal] = {}
    for amount in amounts:
        currency = str(_value(amount, "currency", "")).lower()
        raw_value = _value(amount, "amount")
        if not currency or raw_value is None:
            continue
        if currency not in values:
            order.append(currency)
        values[currency] = Decimal(str(raw_value))
    return order, values


def invoice_display_amounts(invoice: Any) -> list[tuple[str, Decimal]]:
    """Return payable currency alternatives for simple or multi-item invoices."""
    top_level_order, top_level_values = _amount_map(
        _value(invoice, "amounts", []) or []
    )
    if top_level_values:
        return [(currency, top_level_values[currency]) for currency in top_level_order]

    items = _value(invoice, "items", []) or []
    if not items:
        return []

    first_order, first_values = _amount_map(_value(items[0], "amounts", []) or [])
    common_currencies = set(first_values)
    item_values = [first_values]
    for item in items[1:]:
        _, values = _amount_map(_value(item, "amounts", []) or [])
        common_currencies.intersection_update(values)
        item_values.append(values)

    return [
        (
            currency,
            sum(
                (values[currency] for values in item_values),
                start=Decimal("0"),
            ),
        )
        for currency in first_order
        if currency in common_currencies
    ]
