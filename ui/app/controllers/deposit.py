from app.config import Config
from app.exceptions.base import ApplicationError
from app.external.refinance import get_refinance_api_client
from app.middlewares.auth import token_required
from app.schemas import Deposit, DepositStatus, StripeAuthorization, Treasury
from flask import (
    Blueprint,
    flash,
    g,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
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


def _normalize_currency(value: str | None) -> str:
    return str(value or "").strip().upper()


def _format_api_error(exc: ApplicationError, fallback: str) -> str:
    payload = exc.args[0] if exc.args else None
    if isinstance(payload, dict):
        detail = payload.get("error") or payload.get("detail") or payload.get("message")
        if detail:
            return str(detail)
        return str(payload)
    text = str(exc).strip()
    return text or fallback


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
    to_entity_id = HiddenField("", validators=[DataRequired()])

    currency = SelectField(
        "Currency",
        choices=Config.CURRENCY_CHOICES,
        default=Config.PREFERRED_CURRENCY,
        validate_choice=False,
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


class StripeDepositForm(FlaskForm):
    to_entity_id = HiddenField("", validators=[DataRequired()])

    currency = SelectField(
        "Currency",
        choices=Config.CURRENCY_CHOICES,
        default=Config.PREFERRED_CURRENCY,
        validate_choice=False,
        validators=[DataRequired()],
    )
    amount = FloatField(
        "Amount",
        validators=[DataRequired()],
        render_kw={"placeholder": "5.00", "class": "small"},
    )
    submit = SubmitField("Top up")


class StripeAuthorizationSetupForm(FlaskForm):
    entity_id = HiddenField("", validators=[DataRequired()])
    mode = SelectField(
        "Mode",
        choices=[
            ("entity_dynamic", "Entity Dynamic"),
            ("guest_static", "Guest Static"),
        ],
        default="entity_dynamic",
        validators=[DataRequired()],
    )
    static_amount = FloatField(
        "Guest Static Amount",
        validators=[Optional(), NumberRange(min=0.01)],
        render_kw={"placeholder": "10.00", "class": "small"},
    )
    static_currency = SelectField(
        "Guest Static Currency",
        choices=Config.CURRENCY_CHOICES,
        default=Config.PREFERRED_CURRENCY,
        validate_choice=False,
        validators=[Optional()],
    )
    submit = SubmitField("Add Card")


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
        choices=[("", "")] + Config.CURRENCY_CHOICES,
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

    # Always top up the currently authorized entity balance
    form.to_entity_id.data = str(g.actor_entity["id"])

    if form.validate_on_submit():
        api = get_refinance_api_client()
        try:
            params = {
                "to_entity_id": int(form.to_entity_id.data),
                "amount": form.amount.data,
                "currency": _normalize_currency(form.currency.data),
            }
            if form.note.data:
                params["note"] = form.note.data
            response = api.http("POST", "deposits/providers/keepz", params=params)
            result = Deposit(**response.json())
            return redirect(url_for("deposit.detail", id=result.id))
        except Exception as e:
            flash(f"Error creating deposit: {str(e)}", "error")

    return render_template("deposit/add_keepz.jinja2", form=form)


@deposit_bp.route("/stripe/add", methods=["GET", "POST"])
@token_required
def add_stripe():
    form = StripeDepositForm()

    # Always top up the currently authorized entity balance
    form.to_entity_id.data = str(g.actor_entity["id"])

    if form.validate_on_submit():
        api = get_refinance_api_client()
        try:
            params = {
                "to_entity_id": int(form.to_entity_id.data),
                "amount": form.amount.data,
                "currency": _normalize_currency(form.currency.data),
            }
            response = api.http("POST", "deposits/providers/stripe", params=params)
            result = Deposit(**response.json())
            payment_url = ((result.details or {}).get("stripe") or {}).get(
                "payment_url"
            )
            if payment_url:
                return redirect(payment_url)
            return redirect(url_for("deposit.detail", id=result.id))
        except ApplicationError as e:
            flash(
                _format_api_error(e, "Could not create Stripe deposit."),
                "error",
            )
        except Exception as e:
            flash(f"Error creating Stripe deposit: {str(e)}", "error")

    return render_template("deposit/add_stripe.jinja2", form=form)


@deposit_bp.route("/stripe/add-card")
@token_required
def add_stripe_card():
    api = get_refinance_api_client()
    entity_id = int(g.actor_entity["id"])
    try:
        response = api.http(
            "POST",
            "deposits/providers/stripe/authorizations/setup-session",
            params={"entity_id": entity_id, "mode": "entity_dynamic"},
        ).json()
        checkout_url = response.get("checkout_session_url")
        if checkout_url:
            return redirect(checkout_url)
        flash("Stripe setup session created, but no checkout URL returned.", "error")
    except ApplicationError as e:
        flash(_format_api_error(e, "Could not start Stripe card setup."), "error")
    except Exception as e:
        flash(f"Could not start Stripe card setup: {str(e)}", "error")
    return redirect(url_for("deposit.stripe_authorizations"))


@deposit_bp.route("/stripe/charge", methods=["POST"])
@token_required
def charge_stripe_card():
    amount_raw = (request.form.get("amount") or "").strip()
    currency = _normalize_currency(request.form.get("currency"))
    entity_id = int(g.actor_entity["id"])

    try:
        amount = float(amount_raw)
        if amount <= 0:
            raise ValueError("Amount must be positive")
    except (ValueError, TypeError):
        flash("Invalid amount.", "error")
        return redirect(url_for("index.index"))

    api = get_refinance_api_client()
    try:
        response = api.http(
            "POST",
            "deposits/providers/stripe/authorizations/charge",
            params={"entity_id": entity_id, "amount": amount, "currency": currency},
        )
        result = response.json()
        flash(
            f"Charged {amount_raw} {currency} from your card. Deposit #{result.get('id')}.",
            "success",
        )
    except ApplicationError as e:
        flash(_format_api_error(e, "Card charge failed."), "error")
    except Exception as e:
        flash(f"Card charge failed: {str(e)}", "error")

    return redirect(url_for("index.index"))


@deposit_bp.route("/stripe/authorizations", methods=["GET", "POST"])
@token_required
def stripe_authorizations():
    api = get_refinance_api_client()
    actor_id = int(g.actor_entity["id"])
    target_entity_id = request.args.get("entity_id", type=int) or actor_id
    stripe_session_id = (request.args.get("stripe_session_id") or "").strip()

    setup_form = StripeAuthorizationSetupForm()
    setup_form.entity_id.data = str(target_entity_id)

    if request.method == "POST":
        action = (request.form.get("action") or "").strip().lower()
        try:
            if action == "add" and setup_form.validate_on_submit():
                params = {
                    "entity_id": int(setup_form.entity_id.data),
                    "mode": setup_form.mode.data,
                }
                if setup_form.mode.data == "guest_static":
                    params["static_amount"] = setup_form.static_amount.data
                    params["static_currency"] = _normalize_currency(
                        setup_form.static_currency.data
                    )
                response = api.http(
                    "POST",
                    "deposits/providers/stripe/authorizations/setup-session",
                    params=params,
                ).json()
                checkout_url = response.get("checkout_session_url")
                if checkout_url:
                    return redirect(checkout_url)
                flash(
                    "Stripe setup session created, but no checkout URL returned.",
                    "error",
                )
            elif action in {"enable", "disable", "delete", "priority"}:
                auth_id = int(request.form.get("authorization_id", "0") or "0")
                if auth_id <= 0:
                    flash("Invalid authorization id.", "error")
                    return redirect(
                        url_for(
                            "deposit.stripe_authorizations",
                            entity_id=target_entity_id,
                        )
                    )

                if action == "enable":
                    api.http(
                        "POST",
                        f"deposits/providers/stripe/authorizations/{auth_id}/enable",
                    )
                    flash("Card enabled.", "info")
                elif action == "disable":
                    api.http(
                        "POST",
                        f"deposits/providers/stripe/authorizations/{auth_id}/disable",
                    )
                    flash("Card disabled.", "info")
                elif action == "delete":
                    api.http(
                        "DELETE",
                        f"deposits/providers/stripe/authorizations/{auth_id}",
                    )
                    flash("Card deleted.", "info")
                elif action == "priority":
                    priority = int(request.form.get("priority", "1") or "1")
                    api.http(
                        "POST",
                        f"deposits/providers/stripe/authorizations/{auth_id}/priority",
                        params={"priority": max(priority, 1)},
                    )
                    flash("Card priority updated.", "info")
            else:
                flash("Unsupported action.", "error")
        except ApplicationError as e:
            flash(_format_api_error(e, "Stripe authorization action failed."), "error")
        except Exception as e:
            flash(f"Stripe authorization action failed: {str(e)}", "error")

        return redirect(
            url_for("deposit.stripe_authorizations", entity_id=target_entity_id)
        )

    if stripe_session_id:
        try:
            sync_result = api.http(
                "POST",
                "deposits/providers/stripe/authorizations/sync-session",
                params={
                    "checkout_session_id": stripe_session_id,
                    "entity_id": target_entity_id,
                },
            ).json()
            if sync_result and sync_result.get("id"):
                flash("Card authorization synchronized.", "success")
            else:
                flash(
                    "Stripe session was reached, but no authorization was created. "
                    "Please ensure metadata includes entity_id and setup_intent.",
                    "error",
                )
        except ApplicationError as e:
            flash(
                _format_api_error(e, "Could not synchronize Stripe setup session."),
                "error",
            )
        except Exception as e:
            flash(f"Could not synchronize Stripe setup session: {str(e)}", "error")
        return redirect(url_for("index.index"))

    authorizations_resp = api.http(
        "GET",
        "deposits/providers/stripe/authorizations",
        params={"entity_id": target_entity_id},
    ).json()
    authorizations = [
        StripeAuthorization(**item) for item in authorizations_resp.get("items", [])
    ]

    return render_template(
        "deposit/stripe_authorizations.jinja2",
        setup_form=setup_form,
        entity_id=target_entity_id,
        authorizations=authorizations,
    )


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


@deposit_bp.route("/manual")
@token_required
def manual():
    api = get_refinance_api_client()
    resp = api.http("GET", "treasuries", params={"skip": 0, "limit": 500}).json()
    treasuries = [Treasury(**x) for x in resp.get("items", [])]
    active_treasuries = [t for t in treasuries if getattr(t, "active", False)]
    return render_template(
        "deposit/manual.jinja2",
        treasuries=active_treasuries,
    )
