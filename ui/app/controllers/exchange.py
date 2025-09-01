from app.constants import ALLOW_CUSTOM_CURRENCY, CURRENCIES, DEFAULT_CURRENCY
from app.external.refinance import get_refinance_api_client
from app.middlewares.auth import token_required
from app.schemas import CurrencyExchangePreviewResponse, CurrencyExchangeReceipt
from flask import Blueprint, jsonify, redirect, render_template, request, url_for
from flask_wtf import FlaskForm
from wtforms import (
    FloatField,
    IntegerField,
    SelectField,
    StringField,
    SubmitField,
    ValidationError,
)
from wtforms.validators import DataRequired, NumberRange, Optional
from wtforms.widgets import HiddenInput

exchange_bp = Blueprint("exchange", __name__)


class CurrencyExchangeForm(FlaskForm):
    entity_id = IntegerField("", validators=[DataRequired(), NumberRange(min=1)])

    # Source currency dropdown
    currency_choices = CURRENCIES.copy()
    if ALLOW_CUSTOM_CURRENCY:
        currency_choices.append(("other", "Other (custom)"))

    source_currency = SelectField(
        "Source Currency ←",
        choices=currency_choices,
        default="USD",  # Common source for exchange
        validators=[DataRequired()],
        render_kw={"class": "small"},
    )
    source_custom_currency = StringField(
        "Custom Source Currency",
        description="Enter custom currency code",
        render_kw={"placeholder": "XXX", "class": "small"},
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
        choices=currency_choices,
        default=DEFAULT_CURRENCY,
        validators=[DataRequired()],
        render_kw={"class": "small"},
    )
    target_custom_currency = StringField(
        "Custom Target Currency",
        description="Enter custom currency code",
        render_kw={"placeholder": "XXX", "class": "small"},
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

    def validate(self, extra_validators=None):
        """Custom validation to ensure only one amount field is provided"""
        if not super().validate(extra_validators):
            return False

        # Check if both amount fields are filled
        if self.source_amount.data and self.target_amount.data:
            self.source_amount.errors.append(
                "Please provide either source or target amount, not both"
            )
            self.target_amount.errors.append(
                "Please provide either source or target amount, not both"
            )
            return False

        # Check if neither amount field is filled
        if not self.source_amount.data and not self.target_amount.data:
            self.source_amount.errors.append(
                "Please provide either source or target amount"
            )
            self.target_amount.errors.append(
                "Please provide either source or target amount"
            )
            return False

        return True


@exchange_bp.route("/", methods=["GET", "POST"])
@token_required
def index():
    form = CurrencyExchangeForm()
    if form.validate_on_submit():
        data = form.data.copy()

        # Handle custom currency options
        if data.get("source_currency") == "other" and data.get(
            "source_custom_currency"
        ):
            data["source_currency"] = data["source_custom_currency"].lower()
        if data.get("target_currency") == "other" and data.get(
            "target_custom_currency"
        ):
            data["target_currency"] = data["target_custom_currency"].lower()

        # Remove custom currency fields from data
        data.pop("source_custom_currency", None)
        data.pop("target_custom_currency", None)

        api = get_refinance_api_client()
        r = api.http("POST", "currency_exchange/preview", data=data)
        preview = CurrencyExchangePreviewResponse(**r.json())
        return render_template("exchange/preview.jinja2", preview=preview, form=form)
    else:
        return render_template("exchange/index.jinja2", form=form)


@exchange_bp.route("/exchange", methods=["GET", "POST"])
@token_required
def exchange():
    form = CurrencyExchangeForm()
    form.validate_on_submit()

    data = form.data.copy()

    # Handle custom currency options
    if data.get("source_currency") == "other" and data.get("source_custom_currency"):
        data["source_currency"] = data["source_custom_currency"].lower()
    if data.get("target_currency") == "other" and data.get("target_custom_currency"):
        data["target_currency"] = data["target_custom_currency"].lower()

    # Remove custom currency fields from data
    data.pop("source_custom_currency", None)
    data.pop("target_custom_currency", None)

    api = get_refinance_api_client()
    r = api.http("POST", "currency_exchange/exchange", data=data)
    receipt = CurrencyExchangeReceipt(**r.json())
    return render_template("exchange/receipt.jinja2", receipt=receipt)
    # else:
    #     return redirect(url_for("exchange.index"))
