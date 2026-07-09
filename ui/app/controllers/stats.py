from datetime import date

from app.external.refinance import get_refinance_api_client
from flask import Blueprint, render_template, request

stats_bp = Blueprint("stats", __name__, url_prefix="/stats")


@stats_bp.route("/")
def index():
    api = get_refinance_api_client()
    current_month = date.today().strftime("%Y-%m")
    resident_fee_as_of_month = request.args.get(
        "resident_fee_as_of_month", current_month
    )
    try:
        date.fromisoformat(f"{resident_fee_as_of_month}-01")
    except ValueError:
        resident_fee_as_of_month = current_month

    resident_fee_average_params = {
        "as_of_month": f"{resident_fee_as_of_month}-01",
    }

    resident_fee_sum = api.http("GET", "stats/resident-fee-sum-by-month").json()
    resident_fee_average = api.http(
        "GET",
        "stats/resident-fee-average-by-month",
        params=resident_fee_average_params,
    ).json()
    fee_transactions_by_month = api.http(
        "GET", "stats/fee-transactions-by-month"
    ).json()

    return render_template(
        "stats/index.jinja2",
        resident_fee_sum=resident_fee_sum,
        resident_fee_average=resident_fee_average,
        resident_fee_as_of_month=resident_fee_as_of_month,
        fee_transactions_by_month=fee_transactions_by_month,
    )
