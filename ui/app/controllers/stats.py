from app.external.refinance import get_refinance_api_client
from flask import Blueprint, render_template

stats_bp = Blueprint("stats", __name__, url_prefix="/stats")


@stats_bp.route("/")
def index():
    api = get_refinance_api_client()
    monthly_fee_sum = api.http("GET", "stats/monthly-fee-sum-by-month").json()
    fee_transactions_by_month = api.http(
        "GET", "stats/fee-transactions-by-month"
    ).json()[1:]
    donations_by_month = api.http("GET", "stats/donations-by-month").json()

    return render_template(
        "stats/index.jinja2",
        monthly_fee_sum=monthly_fee_sum,
        fee_transactions_by_month=fee_transactions_by_month,
        donations_by_month=donations_by_month,
    )
