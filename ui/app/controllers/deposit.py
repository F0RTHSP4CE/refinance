from flask_wtf import FlaskForm
from wtforms import SelectField, StringField, SubmitField
from app.external.refinance import get_refinance_api_client
from app.middlewares.auth import token_required
from app.schemas import Deposit
from flask import Blueprint, render_template, request

deposit_bp = Blueprint("deposit", __name__)

class DepositFilterForm(FlaskForm):
    currency = StringField("Currency")
    status = SelectField("Status", choices=[("", ""), ("draft", "Draft"), ("completed", "Completed")])
    submit = SubmitField("Filter")

@deposit_bp.route("/")
@token_required
def list():
    page = request.args.get("page", 1, type=int)
    limit = request.args.get("limit", 20, type=int)
    skip = (page - 1) * limit

    filter_form = DepositFilterForm(request.args)
    filters = {
        key: value
        for (key, value) in filter_form.data.items()
        if value not in (None, "", "submit")
    }

    api = get_refinance_api_client()
    response = api.http(
        "GET", "deposits", params={"skip": skip, "limit": limit, **filters}
    ).json()

    deposits = [Deposit(**x) for x in response["items"]]
    total = response["total"]

    return render_template(
        "deposit/list.jinja2",
        deposits=deposits,
        total=total,
        page=page,
        limit=limit,
        filter_form=filter_form,
    )
