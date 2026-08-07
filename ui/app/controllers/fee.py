from datetime import datetime
from decimal import Decimal

from app.external.refinance import get_refinance_api_client
from app.schemas import Fee, MonthlyFee
from flask import Blueprint, render_template

fee_bp = Blueprint("fee", __name__)


FEE_GROUP_BY_TAG_ID = {
    2: "resident",
    14: "member",
    13: "ex-resident",
    18: "ex-member",
}


def _fee_group(entity) -> str:
    tags = entity.get("tags", []) if isinstance(entity, dict) else entity.tags
    tag_ids = {tag.get("id") if isinstance(tag, dict) else tag.id for tag in tags}
    for tag_id in FEE_GROUP_BY_TAG_ID:
        if tag_id in tag_ids:
            return FEE_GROUP_BY_TAG_ID[tag_id]
    return "other"


def _entity_name(entity) -> str:
    if isinstance(entity, dict):
        return str(entity.get("name", "")).lower()
    return entity.name.lower()


@fee_bp.route("/")
def index():
    api = get_refinance_api_client()
    raw_fees = api.http("GET", "fees").json()
    # build Fee objects, converting nested fee dicts to MonthlyFee before constructing
    fees: list[Fee] = []
    for data in raw_fees:
        # convert inner fee dicts to MonthlyFee
        converted = []
        for f in data.get("fees", []):
            raw_amounts = f.get("amounts", {})
            amounts = {
                currency: Decimal(str(value)) for currency, value in raw_amounts.items()
            }
            raw_unpaid_amounts = f.get("unpaid_invoice_amounts") or {}
            unpaid_amounts = {
                currency: Decimal(str(value))
                for currency, value in raw_unpaid_amounts.items()
            }
            converted.append(
                MonthlyFee(
                    year=f["year"],
                    month=f["month"],
                    amounts=amounts,
                    unpaid_invoice_id=f.get("unpaid_invoice_id"),
                    paid_invoice_id=f.get("paid_invoice_id"),
                    unpaid_invoice_amounts=unpaid_amounts,
                )
            )
        data["fees"] = converted
        fees.append(Fee(**data))
    # build unified timeline of (year, month)
    timeline_set = set()
    for rf in fees:
        for f in rf.fees:
            timeline_set.add((f.year, f.month))
    # sort timeline chronologically
    timeline = sorted(timeline_set)
    # Align each entity's monthly fees to the unified timeline.
    for rf in fees:
        fee_map = {(f.year, f.month): f for f in rf.fees}
        rf.fees = []
        for y, m in timeline:
            existing = fee_map.get((y, m))
            if existing is not None:
                rf.fees.append(existing)
            else:
                rf.fees.append(
                    MonthlyFee(
                        year=y,
                        month=m,
                        amounts={},
                        unpaid_invoice_id=None,
                        paid_invoice_id=None,
                        unpaid_invoice_amounts=None,
                    )
                )

    group_order = {
        "resident": 0,
        "member": 1,
        "ex-resident": 2,
        "ex-member": 3,
        "other": 4,
    }

    def _has_unpaid(fee: Fee) -> bool:
        return any(f.unpaid_invoice_id for f in fee.fees)

    def _unpaid_count(fee: Fee) -> int:
        return sum(1 for f in fee.fees if f.unpaid_invoice_id)

    grouped_fees = [(fee, _fee_group(fee.entity)) for fee in fees]
    grouped_fees.sort(
        key=lambda row: (
            group_order[row[1]],
            _has_unpaid(row[0]),
            _unpaid_count(row[0]) if _has_unpaid(row[0]) else 0,
            _entity_name(row[0].entity),
        )
    )
    group_indexes = {key: 0 for key in group_order}
    fee_rows = []
    fees = []
    for fee, group in grouped_fees:
        unpaid_total: dict[str, Decimal] = {}
        for f in fee.fees:
            if f.unpaid_invoice_id and f.unpaid_invoice_amounts:
                for currency, amount in f.unpaid_invoice_amounts.items():
                    unpaid_total[currency] = (
                        unpaid_total.get(currency, Decimal(0)) + amount
                    )
        fees.append(fee)
        fee_rows.append(
            {
                "fee": fee,
                "group": group,
                "index": group_indexes[group],
                "unpaid_total": unpaid_total,
            }
        )
        group_indexes[group] += 1

    group_unpaid_totals: dict[str, dict[str, Decimal]] = {}
    for row in fee_rows:
        g = row["group"]
        for currency, amount in row["unpaid_total"].items():
            if g not in group_unpaid_totals:
                group_unpaid_totals[g] = {}
            group_unpaid_totals[g][currency] = (
                group_unpaid_totals[g].get(currency, Decimal(0)) + amount
            )

    current_date = datetime.utcnow()
    current_month = current_date.month
    current_year = current_date.year
    return render_template(
        "fee/index.jinja2",
        fees=fees,
        fee_rows=fee_rows,
        group_unpaid_totals=group_unpaid_totals,
        current_month=current_month,
        current_year=current_year,
    )
