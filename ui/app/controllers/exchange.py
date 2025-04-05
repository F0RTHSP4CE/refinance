from app.external.refinance import get_refinance_api_client
from app.middlewares.auth import token_required
from app.schemas import CurrencyExchangePreviewResponse, CurrencyExchangeReceipt
from flask import Blueprint, jsonify, redirect, render_template, request, url_for
from flask_wtf import FlaskForm
from wtforms import FloatField, IntegerField, SelectField, StringField, SubmitField
from wtforms.validators import DataRequired, NumberRange, Optional
from wtforms.widgets import HiddenInput

exchange_bp = Blueprint("exchange", __name__)


class CurrencyExchangeForm(FlaskForm):
    entity_id = IntegerField("", validators=[DataRequired(), NumberRange(min=1)])
    source_amount = FloatField(
        "Source Amount",
        render_kw={"placeholder": "10.00", "class": "small"},
        validators=[Optional()],
    )
    source_currency = StringField(
        "Source Currency →",
        description="Amount must be either source or target.<br>Leave another amount blank.",
        validators=[DataRequired()],
        render_kw={"placeholder": "GEL", "class": "small"},
    )
    target_amount = FloatField(
        "Target Amount",
        render_kw={"placeholder": "20.00", "class": "small"},
        validators=[Optional()],
    )
    target_currency = StringField(
        "Target Currency ←",
        validators=[DataRequired()],
        description="Any string, but prefer <a href='https://en.wikipedia.org/wiki/ISO_4217#Active_codes_(list_one)'>ISO 4217</a>. Case insensitive.",
        render_kw={"placeholder": "USD", "class": "small"},
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
    # else:
    #     return redirect(url_for("exchange.index"))
