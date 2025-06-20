from datetime import datetime

from app.external.refinance import get_refinance_api_client
from app.schemas import MonthlyFee, ResidentFee
from flask import Blueprint, render_template, request

resident_fee_bp = Blueprint("resident_fee", __name__, url_prefix="/resident_fee")


@resident_fee_bp.route("/")
def index():
    api = get_refinance_api_client()
    raw_fees = api.http("GET", "resident_fees").json()
    # build ResidentFee objects, converting nested fee dicts to MonthlyFee before constructing
    fees: list[ResidentFee] = []
    for data in raw_fees:
        # convert inner fee dicts to MonthlyFee
        converted = []
        for f in data.get("fees", []):
            converted.append(
                MonthlyFee(
                    year=f["year"], month=f["month"], amounts=f.get("amounts", {})
                )
            )
        data["fees"] = converted
        fees.append(ResidentFee(**data))
    # build unified timeline of (year, month)
    timeline_set = set()
    for rf in fees:
        for f in rf.fees:
            timeline_set.add((f.year, f.month))
    # sort timeline chronologically
    timeline = sorted(timeline_set)
    # align each resident's fees to the unified timeline
    for rf in fees:
        fee_map = {(f.year, f.month): f.amounts for f in rf.fees}
        rf.fees = [
            MonthlyFee(year=y, month=m, amounts=fee_map.get((y, m), {}))
            for y, m in timeline
        ]

    current_date = datetime.utcnow()
    current_month = current_date.month
    current_year = current_date.year
    return render_template(
        "resident_fee/index.jinja2",
        fees=fees,
        current_month=current_month,
        current_year=current_year,
    )
