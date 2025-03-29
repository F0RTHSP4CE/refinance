from app.external.refinance import get_refinance_api_client
from app.middlewares.auth import token_required
from app.schemas import CurrencyExchangePreviewResponse, CurrencyExchangeReceipt
from flask import Blueprint, jsonify, redirect, render_template, request, url_for
from flask_wtf import FlaskForm
from wtforms import FloatField, IntegerField, SelectField, StringField, SubmitField
from wtforms.validators import DataRequired, NumberRange
from wtforms.widgets import HiddenInput

currency_exchange_bp = Blueprint("currency_exchange", __name__)


class CurrencyExchangeForm(FlaskForm):
    entity_name = StringField("Entity")
    entity_id = IntegerField("", validators=[DataRequired(), NumberRange(min=1)])

    source_amount = FloatField(
        "Amount",
        validators=[DataRequired()],
        render_kw={"placeholder": "10.00"},
    )
    source_currency = StringField(
        "Source Currency",
        validators=[DataRequired()],
        render_kw={"placeholder": "GEL, USD"},
    )
    target_currency = StringField(
        "Target Currency",
        validators=[DataRequired()],
        description="Any string, but prefer <a href='https://en.wikipedia.org/wiki/ISO_4217#Active_codes_(list_one)'>ISO 4217</a>. Case insensitive.",
        render_kw={"placeholder": "EUR, RUB"},
    )
    preview = SubmitField("Preview")


@currency_exchange_bp.route("/", methods=["GET", "POST"])
@token_required
def index():
    form = CurrencyExchangeForm()
    if form.validate_on_submit():
        api = get_refinance_api_client()
        r = api.http("POST", "currency_exchange/preview", data=form.data)
        preview = CurrencyExchangePreviewResponse(**r.json())
        return render_template("currency_exchange/preview.jinja2", preview=preview)
    else:
        return render_template("currency_exchange/index.jinja2", form=form)


@currency_exchange_bp.route("/exchange", methods=["GET", "POST"])
@token_required
def exchange():
    form = CurrencyExchangeForm()
    form.validate_on_submit()
    api = get_refinance_api_client()
    r = api.http("POST", "currency_exchange/exchange", data=form.data)
    receipt = CurrencyExchangeReceipt(**r.json())
    return render_template("currency_exchange/receipt.jinja2", receipt=receipt)
    # else:
    #     return redirect(url_for("currency_exchange.index"))
