from collections import defaultdict
from decimal import Decimal

from app.external.refinance import get_refinance_api_client
from app.middlewares.auth import token_required
from flask import Blueprint, g, render_template

index_bp = Blueprint("index", __name__)


@index_bp.route("/")
@token_required
def index():
    api = get_refinance_api_client()
    actor_entity_id = g.actor_entity["id"]

    unpaid_response = api.http(
        "GET",
        "invoices",
        params={
            "status": "pending",
            "from_entity_id": actor_entity_id,
            "skip": 0,
            "limit": 500,
        },
    ).json()

    unpaid_invoices = unpaid_response.get("items", [])
    unpaid_totals = defaultdict(Decimal)
    unpaid_invoice_cards: list[dict[str, object]] = []
    for invoice in unpaid_invoices:
        invoice_id = invoice.get("id")
        invoice_amounts: list[str] = []
        for amount in invoice.get("amounts", []):
            currency = str(amount.get("currency", "")).upper()
            value = amount.get("amount")
            if not currency or value is None:
                continue
            decimal_value = Decimal(str(value)).quantize(Decimal("0.01"))
            unpaid_totals[currency] += decimal_value
            invoice_amounts.append(f"{format(decimal_value, 'f')} {currency}")

        if invoice_id is not None and invoice_amounts:
            unpaid_invoice_cards.append(
                {
                    "id": int(invoice_id),
                    "amounts": invoice_amounts,
                }
            )

    unpaid_fee_summary = [
        f"{total.quantize(Decimal('0.01'))} {currency}"
        for currency, total in sorted(unpaid_totals.items())
        if total > 0
    ]

    return render_template(
        "index.jinja2",
        unpaid_fee_count=len(unpaid_invoices),
        unpaid_fee_summary=unpaid_fee_summary,
        unpaid_invoice_cards=unpaid_invoice_cards,
    )
