from app.external.refinance import get_refinance_api_client
from flask import Blueprint, render_template

stats_bp = Blueprint("stats", __name__, url_prefix="/stats")


@stats_bp.route("/")
def index():
    api = get_refinance_api_client()
    resident_fee_sum = api.http("GET", "stats/resident-fee-sum-by-month").json()
    resident_fee_average = api.http("GET", "stats/resident-fee-average-by-month").json()
    fee_transactions_by_month = api.http(
        "GET", "stats/fee-transactions-by-month"
    ).json()

    return render_template(
        "stats/index.jinja2",
        resident_fee_sum=resident_fee_sum,
        resident_fee_average=resident_fee_average,
        fee_transactions_by_month=fee_transactions_by_month,
    )
