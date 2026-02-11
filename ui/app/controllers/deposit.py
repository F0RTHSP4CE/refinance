from app.external.refinance import get_refinance_api_client
from app.middlewares.auth import token_required
from app.schemas import Deposit, DepositStatus
from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from flask_wtf import FlaskForm
from wtforms import (
    FloatField,
    HiddenField,
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


class KeepzDepositForm(FlaskForm):
    to_entity_name = StringField("To Entity")
    to_entity_id = IntegerField("", validators=[DataRequired(), NumberRange(min=1)])

    currency = SelectField(
        "Currency",
        choices=[("GEL", "GEL"), ("USD", "USD"), ("EUR", "EUR")],
        validators=[DataRequired()],
    )
    amount = FloatField(
        "Amount",
        validators=[DataRequired()],
        render_kw={"placeholder": "5.00", "class": "small"},
    )
    note = StringField(
        "Note",
        validators=[Optional()],
        render_kw={"placeholder": "optional"},
        description="Optional note for matching payments.",
    )
    submit = SubmitField("Create Deposit")


class KeepzAuthForm(FlaskForm):
    phone = StringField(
        "Phone",
        validators=[DataRequired()],
        render_kw={"placeholder": "555123456"},
    )
    country_code = StringField(
        "Country Code",
        validators=[DataRequired()],
        render_kw={"placeholder": "+995"},
    )
    code = StringField(
        "OTP",
        validators=[Optional()],
        render_kw={"placeholder": "123456"},
    )
    user_type = HiddenField(default="INDIVIDUAL")
    device_token = HiddenField(default="")
    mobile_name = HiddenField(default="iPhone 12 mini")
    mobile_os = HiddenField(default="IOS")
    send_sms = SubmitField("Send SMS")
    verify_login = SubmitField("Verify & Login")


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


@deposit_bp.route("/keepz/add", methods=["GET", "POST"])
@token_required
def add_keepz():
    form = KeepzDepositForm()

    if form.validate_on_submit():
        api = get_refinance_api_client()
        try:
            params = {
                "to_entity_id": form.to_entity_id.data,
                "amount": form.amount.data,
                "currency": form.currency.data,
            }
            if form.note.data:
                params["note"] = form.note.data
            response = api.http("POST", "deposits/providers/keepz", params=params)
            result = Deposit(**response.json())
            return redirect(url_for("deposit.detail", id=result.id))
        except Exception as e:
            flash(f"Error creating deposit: {str(e)}", "error")

    return render_template("deposit/add_keepz.jinja2", form=form)


@deposit_bp.route("/keepz/auth", methods=["GET", "POST"])
@token_required
def keepz_auth():
    form = KeepzAuthForm()
    api = get_refinance_api_client()
    status = None

    if form.validate_on_submit():
        try:
            if form.send_sms.data:
                api.http(
                    "POST",
                    "keepz/auth/send-sms",
                    data={
                        "phone": form.phone.data,
                        "country_code": form.country_code.data,
                    },
                )
                flash("SMS sent. Enter the OTP to finish login.", "info")
            elif form.verify_login.data:
                api.http(
                    "POST",
                    "keepz/auth/login",
                    data={
                        "phone": form.phone.data,
                        "country_code": form.country_code.data,
                        "code": form.code.data,
                        "user_type": form.user_type.data,
                        "device_token": form.device_token.data,
                        "mobile_name": form.mobile_name.data,
                        "mobile_os": form.mobile_os.data,
                    },
                )
                flash("Keepz authenticated.", "info")
        except Exception as e:
            flash(f"Keepz auth failed: {str(e)}", "error")

    try:
        status = api.http("GET", "keepz/auth/status").json()
    except Exception as e:
        flash(f"Keepz status error: {str(e)}", "error")

    return render_template("deposit/keepz_auth.jinja2", form=form, status=status)


@deposit_bp.route("/<int:id>")
@token_required
def detail(id):
    api = get_refinance_api_client()
    response = api.http("GET", f"deposits/{id}")
    deposit = Deposit(**response.json())
    return render_template("deposit/detail.jinja2", deposit=deposit)
