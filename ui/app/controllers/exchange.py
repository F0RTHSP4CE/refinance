from app.external.refinance import get_refinance_api_client
from app.middlewares.auth import token_required
from app.schemas import (
    AutoBalanceEntityPlan,
    AutoBalanceEntityReceipt,
    AutoBalanceExchangeItem,
    AutoBalancePreview,
    AutoBalanceRunResult,
    CurrencyExchangePreviewResponse,
    CurrencyExchangeReceipt,
)
from flask import Blueprint, render_template, request, url_for
from flask_wtf import FlaskForm
from wtforms import FloatField, IntegerField, SelectField, StringField, SubmitField
from wtforms.validators import DataRequired, NumberRange, Optional
from wtforms.widgets import HiddenInput

exchange_bp = Blueprint("exchange", __name__)


class CurrencyExchangeForm(FlaskForm):
    entity_id = IntegerField("", validators=[DataRequired(), NumberRange(min=1)])
    source_currency = SelectField(
        "Source Currency ←",
        choices=[("GEL", "GEL"), ("USD", "USD"), ("EUR", "EUR")],
        default="GEL",
        validators=[DataRequired()],
    )
    source_amount = FloatField(
        "Source Amount",
        render_kw={"placeholder": "10.00", "class": "small"},
        description="Leave empty if target amount is provided.",
        validators=[
            Optional(),
            NumberRange(min=0.01, message="Amount must be greater than 0"),
        ],
    )
    target_currency = SelectField(
        "Target Currency →",
        choices=[("GEL", "GEL"), ("USD", "USD"), ("EUR", "EUR")],
        default="GEL",
        validators=[DataRequired()],
    )
    target_amount = FloatField(
        "Target Amount",
        render_kw={"placeholder": "27.00", "class": "small"},
        description="Leave empty if source amount is provided.",
        validators=[
            Optional(),
            NumberRange(min=0.01, message="Amount must be greater than 0"),
        ],
    )

    entity_name = StringField("Entity")


@exchange_bp.route("/", methods=["GET", "POST"])
@token_required
def index():
    form = CurrencyExchangeForm()
    if form.validate_on_submit():
        api = get_refinance_api_client()
        r = api.http("POST", "currency_exchange/preview", data=form.data)
        preview = CurrencyExchangePreviewResponse(**r.json())
        return render_template("exchange/preview.jinja2", preview=preview, form=form)
    else:
        return render_template("exchange/index.jinja2", form=form)


@exchange_bp.route("/exchange", methods=["GET", "POST"])
@token_required
def exchange():
    form = CurrencyExchangeForm()
    form.validate_on_submit()
    api = get_refinance_api_client()
    r = api.http("POST", "currency_exchange/exchange", data=form.data)
    receipt = CurrencyExchangeReceipt(**r.json())
    return render_template("exchange/receipt.jinja2", receipt=receipt)


@exchange_bp.route("/auto_balance", methods=["GET"])
@token_required
def auto_balance_preview():
    """Show preview of auto-balance exchanges for all eligible entities."""
    api = get_refinance_api_client()
    r = api.http("GET", "currency_exchange/auto_balance/preview")
    data = r.json()
    plans = [
        AutoBalanceEntityPlan(
            entity_id=p["entity_id"],
            entity_name=p["entity_name"],
            exchanges=[
                AutoBalanceExchangeItem(
                    source_currency=e["source_currency"],
                    source_amount=e["source_amount"],
                    target_currency=e["target_currency"],
                    target_amount=e["target_amount"],
                    rate=e["rate"],
                )
                for e in p["exchanges"]
            ],
        )
        for p in data["plans"]
    ]
    preview = AutoBalancePreview(plans=plans)
    return render_template("exchange/auto_balance.jinja2", preview=preview)


@exchange_bp.route("/auto_balance/run", methods=["POST"])
@token_required
def auto_balance_run():
    """Execute auto-balance exchanges for all eligible entities."""
    api = get_refinance_api_client()
    r = api.http("POST", "currency_exchange/auto_balance/run")
    data = r.json()
    results = [
        AutoBalanceEntityReceipt(
            entity_id=res["entity_id"],
            entity_name=res["entity_name"],
            receipts=res["receipts"],
        )
        for res in data["results"]
    ]
    run_result = AutoBalanceRunResult(results=results)
    return render_template("exchange/auto_balance_result.jinja2", run_result=run_result)
