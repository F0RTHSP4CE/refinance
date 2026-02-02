from app.external.refinance import get_refinance_api_client
from app.middlewares.auth import token_required
from app.schemas import Deposit, DepositStatus
from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from flask_wtf import FlaskForm
from wtforms import (
    FloatField,
    IntegerField,
    SelectField,
    SelectMultipleField,
    StringField,
    SubmitField,
)
from wtforms.validators import DataRequired, NumberRange, Optional

deposit_bp = Blueprint("deposit", __name__)


class CryptAPIDepositForm(FlaskForm):
    to_entity_name = StringField("To Entity")
    to_entity_id = IntegerField("", validators=[DataRequired(), NumberRange(min=1)])

    coin = SelectField(
        "Coin",
        choices=[
            ("erc20/usdt", "USDT (ERC20) - min  5.00 USD"),
            ("trc20/usdt", "USDT (TRC20) - min 15.00 USD"),
        ],
        validators=[DataRequired()],
    )
    amount = FloatField(
        "Amount",
        validators=[
            DataRequired(),
        ],
        render_kw={"placeholder": "5.00", "class": "small"},
        description="Fees are calculated automatically by CryptAPI, actual deposited amount can vary ⚠️ <a href='https://cryptapi.io/cryptocurrencies' target='_blank'>See fees</a>",
    )
    submit = SubmitField("Create Deposit")


class DepositFilterForm(FlaskForm):
    entity_name = StringField("Entity (To/Actor)")
    entity_id = IntegerField("", validators=[NumberRange(min=1)])
    actor_entity_name = StringField("Actor")
    actor_entity_id = IntegerField("", validators=[NumberRange(min=1)])
    from_entity_name = StringField("From")
    from_entity_id = IntegerField("", validators=[NumberRange(min=1)])
    to_entity_name = StringField("To")
    to_entity_id = IntegerField("", validators=[NumberRange(min=1)])
    amount_min = FloatField(
        "Amount Min",
        render_kw={"placeholder": "10.00", "class": "small"},
        validators=[
            Optional(),
            NumberRange(min=0, message="Amount must be non-negative"),
        ],
    )
    amount_max = FloatField(
        "Amount Max",
        render_kw={"placeholder": "20.00", "class": "small"},
        validators=[
            Optional(),
            NumberRange(min=0, message="Amount must be non-negative"),
        ],
    )
    currency = SelectField(
        "Currency",
        choices=[("", ""), ("GEL", "GEL"), ("USD", "USD"), ("EUR", "EUR")],
    )
    status = SelectField(
        "Status", choices=[("", "")] + [(e.value, e.value) for e in DepositStatus]
    )
    provider = StringField(
        "Provider",
        render_kw={"placeholder": "cryptapi", "class": "small"},
    )
    submit = SubmitField("Search")


@deposit_bp.route("/")
@token_required
def list():
    # Get the current page and limit from query parameters, defaulting to page 1 and 20 items per page.
    page = request.args.get("page", 1, type=int)
    limit = request.args.get("limit", 20, type=int)
    skip = (page - 1) * limit

    filter_form = DepositFilterForm(request.args)
    # leave only non-empty filters
    filters = {
        key: value
        for (key, value) in filter_form.data.items()
        if value not in (None, "")
    }

    api = get_refinance_api_client()
    # Pass skip and limit to the FastAPI endpoint
    response = api.http(
        "GET", "deposits", params={"skip": skip, "limit": limit, **filters}
    ).json()

    # Extract deposits and pagination details from the API response
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


@deposit_bp.route("/cryptapi/add", methods=["GET", "POST"])
@token_required
def add_cryptapi():
    form = CryptAPIDepositForm()

    if form.validate_on_submit():
        api = get_refinance_api_client()
        try:
            response = api.http(
                "POST",
                "deposits/providers/cryptapi",
                params={
                    "to_entity_id": form.to_entity_id.data,
                    "amount": form.amount.data,
                    "coin": form.coin.data,
                },
            )
            result = Deposit(**response.json())
            return redirect(url_for("deposit.detail", id=result.id))
        except Exception as e:
            flash(f"Error creating deposit: {str(e)}", "error")

    return render_template("deposit/add_cryptapi.jinja2", form=form)


@deposit_bp.route("/<int:id>")
@token_required
def detail(id):
    api = get_refinance_api_client()
    response = api.http("GET", f"deposits/{id}")
    deposit = Deposit(**response.json())
    return render_template("deposit/detail.jinja2", deposit=deposit)
