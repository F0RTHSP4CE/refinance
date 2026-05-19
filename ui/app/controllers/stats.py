from app.external.refinance import get_refinance_api_client
from flask import Blueprint, render_template

stats_bp = Blueprint("stats", __name__, url_prefix="/stats")


@stats_bp.route("/")
def index():
    api = get_refinance_api_client()
    resident_fee_accumulation = api.http(
        "GET", "stats/resident-fee-accumulation-by-month"
    ).json()
    transactions_sum_by_week = api.http("GET", "stats/transactions-sum-by-week").json()

    return render_template(
        "stats/index.jinja2",
        resident_fee_accumulation=resident_fee_accumulation,
        transactions_sum_by_week=transactions_sum_by_week,
    )
