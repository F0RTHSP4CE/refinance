from datetime import datetime
from decimal import Decimal

from app.external.refinance import get_refinance_api_client
from app.schemas import Fee, MonthlyFee
from flask import Blueprint, render_template, request

fee_bp = Blueprint("fee", __name__)


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
            total_usd_raw = f.get("total_usd", 0)
            total_usd = Decimal(str(total_usd_raw or 0))
            converted.append(
                MonthlyFee(
                    year=f["year"],
                    month=f["month"],
                    amounts=amounts,
                    total_usd=total_usd,
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
    # align each resident's fees to the unified timeline
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
                        total_usd=Decimal("0"),
                        unpaid_invoice_id=None,
                        paid_invoice_id=None,
                        unpaid_invoice_amounts=None,
                    )
                )

        rf.total_usd_series = [fee.total_usd for fee in rf.fees]
        max_total = max(rf.total_usd_series, default=Decimal("0"))
        rf.max_total_usd = max_total
        width = Decimal("90")
        height = Decimal("24")
        padding_x = Decimal("2")
        padding_y = Decimal("2")
        usable_width = width - padding_x * 2
        usable_height = height - padding_y * 2
        if usable_width <= 0:
            usable_width = width
            padding_x = Decimal("0")
        if usable_height <= 0:
            usable_height = height
            padding_y = Decimal("0")
        scale = max_total if max_total > 0 else Decimal("1")
        count = len(rf.total_usd_series)
        dot_points: list[tuple[float, float]] = []
        segments: list[list[tuple[float, float]]] = []
        current_segment: list[tuple[float, float]] = []

        for idx, value in enumerate(rf.total_usd_series):
            if count <= 1:
                x = width / Decimal("2")
            else:
                x = padding_x + (Decimal(idx) / Decimal(count - 1)) * usable_width
            try:
                ratio = (Decimal(value) / scale) if scale > 0 else Decimal("0")
            except Exception:
                ratio = Decimal("0")
            if ratio < 0:
                ratio = Decimal("0")
            if ratio > 1:
                ratio = Decimal("1")
            y = padding_y + (Decimal("1") - ratio) * usable_height
            point = (float(x), float(y))

            if value > 0:
                dot_points.append(point)
                current_segment.append(point)
            else:
                if len(current_segment) >= 1:
                    segments.append(current_segment)
                    current_segment = []

        if current_segment:
            segments.append(current_segment)

        rf.sparkline_points = ""
        rf.sparkline_segments = [
            " ".join(f"{x:.2f},{y:.2f}" for x, y in segment)
            for segment in segments
            if len(segment) >= 2
        ]
        rf.sparkline_dots = dot_points
        rf.sparkline_last_point = dot_points[-1] if dot_points else None

    current_date = datetime.utcnow()
    current_month = current_date.month
    current_year = current_date.year
    return render_template(
        "fee/index.jinja2",
        fees=fees,
        current_month=current_month,
        current_year=current_year,
    )
