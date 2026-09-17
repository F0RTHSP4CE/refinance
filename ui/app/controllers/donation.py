import re
from decimal import Decimal, InvalidOperation

from app.config import Config
from app.exceptions.base import ApplicationError
from app.external.refinance import RefinanceAPI
from flask import Blueprint, flash, redirect, render_template, request, session, url_for

donation_bp = Blueprint("donation", __name__)

DONATION_CURRENCIES = ("GEL", "USD", "EUR")
AMOUNT_PATTERN = re.compile(r"^\d+(?:[\.,]\d{1,2})?$")
DONATION_FORM_SESSION_KEY = "donation_form"


def _format_amount(amount: Decimal) -> str:
    formatted = format(amount, "f")
    return formatted.rstrip("0").rstrip(".") if "." in formatted else formatted


def _parse_amount(raw_amount: str) -> Decimal:
    normalized = raw_amount.replace(" ", "").replace(",", ".")
    if not normalized:
        raise ValueError("Enter a donation amount.")
    if not AMOUNT_PATTERN.fullmatch(normalized):
        raise ValueError("Enter a valid donation amount with up to 2 decimal places.")

    try:
        amount = Decimal(normalized)
    except InvalidOperation as exc:
        raise ValueError("Enter a valid donation amount.") from exc

    if amount < Config.DONATION_MIN_AMOUNT:
        raise ValueError(
            f"Donation amount must be at least {_format_amount(Config.DONATION_MIN_AMOUNT)}."
        )
    if amount > Config.DONATION_MAX_AMOUNT:
        raise ValueError(
            f"Donation amount must be at most {_format_amount(Config.DONATION_MAX_AMOUNT)}."
        )
    return amount


def _slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def _fetch_recipients() -> list[dict]:
    try:
        return RefinanceAPI(token=None).http("GET", "donations/recipients").json()
    except Exception:
        # Donations can still target the API's default recipient.
        return []


def _match_recipient(recipients: list[dict], value: str | None) -> dict | None:
    value = (value or "").strip()
    if not value:
        return None
    if value.isdigit():
        recipient_id = int(value)
        return next((item for item in recipients if item["id"] == recipient_id), None)
    slug = _slugify(value)
    return next((item for item in recipients if _slugify(item["name"]) == slug), None)


def _default_recipient(recipients: list[dict]) -> str:
    if not recipients:
        return ""
    general = next((item for item in recipients if item.get("general")), recipients[0])
    return str(general["id"])


def _recipient_payload(recipients: list[dict], value: str) -> dict:
    value = value.strip()
    if not value:
        return {}
    recipient = _match_recipient(recipients, value)
    if recipient:
        return {"recipient_entity_id": recipient["id"]}
    if value.isdigit():
        # Let the API distinguish a stale selection from an invalid recipient.
        return {"recipient_entity_id": int(value)}
    raise ValueError("Select a valid donation destination.")


def _initial_form(recipients: list[dict]) -> dict[str, str]:
    form = {
        "type": "recurring" if Config.STRIPE_CONFIGURED else "onetime",
        "amount": "10",
        "currency": "USD",
        "comment": "",
        "recipient": _default_recipient(recipients),
    }

    saved = session.get(DONATION_FORM_SESSION_KEY)
    if isinstance(saved, dict):
        saved_type = saved.get("type")
        if saved_type == "onetime" or (
            saved_type == "recurring" and Config.STRIPE_CONFIGURED
        ):
            form["type"] = saved_type

        saved_amount = saved.get("amount")
        if isinstance(saved_amount, str):
            try:
                _parse_amount(saved_amount)
            except ValueError:
                pass
            else:
                form["amount"] = saved_amount

        saved_currency = saved.get("currency")
        if saved_currency in DONATION_CURRENCIES:
            form["currency"] = saved_currency

        saved_comment = saved.get("comment")
        if isinstance(saved_comment, str):
            form["comment"] = saved_comment

        saved_recipient = _match_recipient(recipients, saved.get("recipient"))
        if saved_recipient:
            form["recipient"] = str(saved_recipient["id"])

    deep_link_recipient = _match_recipient(recipients, request.args.get("to"))
    if deep_link_recipient:
        form["recipient"] = str(deep_link_recipient["id"])
    return form


def _submitted_form(defaults: dict[str, str]) -> dict[str, str]:
    form = {}
    for key, default in defaults.items():
        value = request.form.get(key)
        form[key] = (default if value is None else value).strip()
    form["type"] = form["type"].lower()
    form["currency"] = form["currency"].upper()
    return form


def _submit_donation(form: dict[str, str], recipients: list[dict]) -> str:
    donation_type = form["type"]
    if donation_type not in {"onetime", "recurring"}:
        raise ValueError("Select a valid donation frequency.")
    if donation_type == "recurring" and not Config.STRIPE_CONFIGURED:
        raise ValueError("Recurring donations are not available at this time.")
    if form["currency"] not in DONATION_CURRENCIES:
        raise ValueError("Select a valid currency.")

    payload = {
        "amount": str(_parse_amount(form["amount"])),
        "currency": form["currency"],
        "comment": form["comment"],
        **_recipient_payload(recipients, form["recipient"]),
    }
    api = RefinanceAPI(token=None)

    if donation_type == "recurring":
        payload.update(
            success_url=url_for("donation.subscribed", _external=True)
            + "?stripe_session_id={CHECKOUT_SESSION_ID}",
            cancel_url=url_for("donation.donate", _external=True),
        )
        result = api.http("POST", "donations/subscribe", data=payload).json()
        if checkout_url := result.get("checkout_session_url"):
            return checkout_url
        raise ApplicationError("Stripe did not return a checkout URL.")

    result = api.http("POST", "donations", data=payload).json()
    if payment_url := result.get("payment_url"):
        return payment_url
    if deposit_uuid := result.get("deposit_uuid"):
        return url_for("donation.pending", deposit_uuid=deposit_uuid)
    raise ApplicationError("The payment provider did not return a payment URL.")


@donation_bp.route("/", methods=["GET", "POST"])
def donate():
    recipients = _fetch_recipients()
    form = _initial_form(recipients)

    if request.method == "POST":
        form = _submitted_form(form)
        session[DONATION_FORM_SESSION_KEY] = form
        try:
            destination = _submit_donation(form, recipients)
            return redirect(destination)
        except ValueError as exc:
            flash(str(exc), "error")
        except ApplicationError as exc:
            flash(f"Could not create donation: {exc}", "error")

    return render_template(
        "donation/donate.jinja2",
        form=form,
        donation_min_amount=Config.DONATION_MIN_AMOUNT,
        donation_max_amount=Config.DONATION_MAX_AMOUNT,
        stripe_configured=Config.STRIPE_CONFIGURED,
        recipients=recipients,
    )


@donation_bp.route("/pending/<string:deposit_uuid>")
def pending(deposit_uuid: str):
    try:
        donation = (
            RefinanceAPI(token=None).http("GET", f"donations/{deposit_uuid}").json()
        )
    except ApplicationError:
        flash("Donation not found.", "error")
        return redirect(url_for("donation.donate"))
    return render_template("donation/pending.jinja2", donation=donation)


@donation_bp.route("/subscribed")
def subscribed():
    session_id = (request.args.get("stripe_session_id") or "").strip()
    portal_url = None
    if session_id:
        api = RefinanceAPI(token=None)
        try:
            api.http(
                "POST",
                "donations/subscribe/sync",
                params={"checkout_session_id": session_id},
            )
        except ApplicationError as exc:
            flash(f"Could not confirm subscription: {exc}", "error")

        try:
            portal_url = (
                api.http(
                    "GET",
                    "donations/portal",
                    params={
                        "checkout_session_id": session_id,
                        "return_url": url_for("donation.donate", _external=True),
                    },
                )
                .json()
                .get("portal_url")
            )
        except ApplicationError:
            pass  # The subscription succeeded even if its management link failed.

    return render_template("donation/subscribed.jinja2", portal_url=portal_url)
