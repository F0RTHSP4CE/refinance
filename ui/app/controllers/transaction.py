from flask import Blueprint, render_template

from ui.external.refinance import get_refinance_api_client
from ui.middlewares.auth import token_required
from ui.schemas import Transaction

transaction_bp = Blueprint("transaction", __name__)


@transaction_bp.route("/")
@token_required
def list():
    api = get_refinance_api_client()
    return render_template(
        "transaction/list.jinja2",
        transactions=[
            Transaction(**x) for x in api.http("GET", "transactions").json()["items"]
        ],
    )


@transaction_bp.route("/<int:id>")
@token_required
def detail(id):
    api = get_refinance_api_client()
    return render_template(
        "transaction/detail.jinja2",
        transaction=Transaction(**api.http("GET", f"transactions/{id}").json()),
    )
