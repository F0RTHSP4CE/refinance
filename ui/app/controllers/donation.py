import re
from decimal import Decimal, InvalidOperation

from app.config import Config
from app.exceptions.base import ApplicationError
from app.external.refinance import RefinanceAPI
from flask import Blueprint, flash, redirect, render_template, request, url_for

donation_bp = Blueprint("donation", __name__)

DONATION_PRESET_AMOUNTS = ("5", "10", "25")
DONATION_CURRENCY = "USD"
DONATION_CURRENCY_SYMBOL = "$"
DONATION_AMOUNT_PATTERN = re.compile(r"^\d+(?:[\.,]\d{1,2})?$")
RECURRING_CURRENCIES = ["GEL", "USD", "EUR"]


def _format_amount(amount: Decimal) -> str:
    return format(amount.normalize(), "f").rstrip("0").rstrip(".") or "0"


def _parse_amount(raw_amount: str) -> Decimal:
    normalized_amount = (
        raw_amount.upper()
        .replace(DONATION_CURRENCY, "")
        .replace(DONATION_CURRENCY_SYMBOL, "")
        .replace(" ", "")
        .strip()
    )

    if not normalized_amount:
        raise ValueError("Enter a donation amount.")
    if not DONATION_AMOUNT_PATTERN.fullmatch(normalized_amount):
        raise ValueError("Enter a valid donation amount with up to 2 decimal places.")

    try:
        amount = Decimal(normalized_amount.replace(",", "."))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("Enter a valid donation amount.") from exc

    if amount <= 0:
        raise ValueError("Donation amount must be greater than 0.")
    if amount < Config.DONATION_MIN_AMOUNT:
        raise ValueError(
            "Donation amount must be at least "
            f"{_format_amount(Config.DONATION_MIN_AMOUNT)} {DONATION_CURRENCY_SYMBOL}."
        )
    if amount > Config.DONATION_MAX_AMOUNT:
        raise ValueError(
            "Donation amount must be at most "
            f"{_format_amount(Config.DONATION_MAX_AMOUNT)} {DONATION_CURRENCY_SYMBOL}."
        )

    return amount


def _submitted_amount(form_data: dict[str, str]) -> Decimal:
    custom_amount = form_data["custom_amount"].strip()
    if custom_amount:
        return _parse_amount(custom_amount)

    preset_amount = form_data["preset_amount"].strip()
    if not preset_amount:
        raise ValueError("Select a donation amount or enter another amount.")
    if preset_amount not in DONATION_PRESET_AMOUNTS:
        raise ValueError("Select one of the available donation amounts.")

    return _parse_amount(preset_amount)


def _slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def _fetch_recipients() -> list[dict]:
    """Public list of donation destinations: F0 (general) first, then rooms."""
    try:
        api = RefinanceAPI(token=None)
        raw = api.http("GET", "donations/recipients").json()
    except Exception:
        return []  # selector is hidden; the API falls back to the general space
    return [
        {**r, "label": f"{r['name']} (general)" if r.get("general") else r["name"]}
        for r in raw
    ]


def _match_recipient(recipients: list[dict], raw: str | None) -> dict | None:
    """Match a recipient by numeric id or slugified name (e.g. 'music-studio')."""
    raw = (raw or "").strip()
    if not raw:
        return None
    if raw.isdigit():
        entity_id = int(raw)
        return next((r for r in recipients if r["id"] == entity_id), None)
    slug = _slugify(raw)
    return next((r for r in recipients if _slugify(r["name"]) == slug), None)


def _recipient_payload(recipients: list[dict], raw_value: str) -> dict:
    """API payload fragment for the submitted recipient field."""
    raw_value = (raw_value or "").strip()
    if not raw_value:
        return {}
    selected = _match_recipient(recipients, raw_value)
    if selected:
        return {"recipient_entity_id": selected["id"]}
    if raw_value.isdigit():
        # unknown id (e.g. recipients list unavailable) — let the API validate it
        return {"recipient_entity_id": int(raw_value)}
    raise ValueError("Select a valid donation destination.")


@donation_bp.route("/", methods=["GET", "POST"])
def donate():
    recipients = _fetch_recipients()
    default_destination = _match_recipient(recipients, "hackerspace")
    default_recipient = (
        str(default_destination["id"] if default_destination else recipients[0]["id"])
        if recipients
        else ""
    )
    default_donation_type = "recurring" if Config.STRIPE_CONFIGURED else "onetime"

    form_data = {
        "comment": "",
        "recurring_comment": "",
        "preset_amount": "10",
        "custom_amount": "",
        "type": default_donation_type,
        "onetime_currency": "USD",
        "recurring_preset_amount": "10",
        "recurring_custom_amount": "",
        "recurring_currency": "USD",
        "onetime_recipient": default_recipient,
        "recurring_recipient": default_recipient,
    }

    # deep links: /donate?to=<room id or slug> preselects the destination
    preselected = _match_recipient(recipients, request.args.get("to"))
    if preselected:
        form_data["onetime_recipient"] = str(preselected["id"])
        form_data["recurring_recipient"] = str(preselected["id"])

    if request.method == "POST":
        donation_type = (
            (request.form.get("type") or default_donation_type).strip().lower()
        )
        if "amount" in request.form:
            # The current UI is one form with one set of values. Donation type
            # only selects the payment path; it must not select another copy of
            # amount, currency, comment, or recipient.
            shared_amount = (request.form.get("amount") or "").strip()
            shared_currency = (request.form.get("currency") or "USD").strip().upper()
            shared_comment = (request.form.get("comment") or "").strip()
            shared_recipient = (
                request.form.get("recipient") or default_recipient
            ).strip()
            form_data = {
                "comment": shared_comment,
                "recurring_comment": shared_comment,
                "preset_amount": "",
                "custom_amount": shared_amount,
                "type": donation_type,
                "onetime_currency": shared_currency,
                "recurring_preset_amount": "",
                "recurring_custom_amount": shared_amount,
                "recurring_currency": shared_currency,
                "onetime_recipient": shared_recipient,
                "recurring_recipient": shared_recipient,
            }
        else:
            # Accept submissions from an already-open copy of the previous UI.
            form_data = {
                "comment": (request.form.get("comment") or "").strip(),
                "recurring_comment": (
                    request.form.get("recurring_comment") or ""
                ).strip(),
                "preset_amount": (request.form.get("preset_amount") or "").strip(),
                "custom_amount": (request.form.get("custom_amount") or "").strip(),
                "type": donation_type,
                "onetime_currency": (request.form.get("onetime_currency") or "USD")
                .strip()
                .upper(),
                "recurring_preset_amount": (
                    request.form.get("recurring_preset_amount") or ""
                ).strip(),
                "recurring_custom_amount": (
                    request.form.get("recurring_custom_amount") or ""
                ).strip(),
                "recurring_currency": (request.form.get("recurring_currency") or "USD")
                .strip()
                .upper(),
                "onetime_recipient": (
                    request.form.get("onetime_recipient") or default_recipient
                ).strip(),
                "recurring_recipient": (
                    request.form.get("recurring_recipient") or default_recipient
                ).strip(),
            }

        if donation_type == "recurring":
            try:
                if not Config.STRIPE_CONFIGURED:
                    raise ValueError(
                        "Recurring donations are not available at this time."
                    )
                recurring_custom = form_data["recurring_custom_amount"]
                recurring_preset = form_data["recurring_preset_amount"]
                recurring_amount_raw = recurring_custom or recurring_preset
                if not recurring_amount_raw:
                    raise ValueError("Select a monthly amount or enter another amount.")
                amount = _parse_amount(recurring_amount_raw)
                currency = form_data["recurring_currency"]
                if currency not in RECURRING_CURRENCIES:
                    raise ValueError("Select a valid currency.")
                recipient = _recipient_payload(
                    recipients, form_data["recurring_recipient"]
                )

                success_url = (
                    url_for("donation.subscribed", _external=True)
                    + "?stripe_session_id={CHECKOUT_SESSION_ID}"
                )
                cancel_url = url_for("donation.donate", _external=True)

                api = RefinanceAPI(token=None)
                response = api.http(
                    "POST",
                    "donations/subscribe",
                    data={
                        "amount": str(amount),
                        "currency": currency,
                        "comment": form_data["recurring_comment"],
                        "success_url": success_url,
                        "cancel_url": cancel_url,
                        **recipient,
                    },
                ).json()
                checkout_url = response.get("checkout_session_url")
                if checkout_url:
                    return redirect(checkout_url)
                flash(
                    "Could not create subscription: no checkout URL returned.", "error"
                )
            except ValueError as e:
                flash(str(e), "error")
            except ApplicationError as e:
                flash(f"Could not create subscription: {e}", "error")
        else:
            try:
                amount = _submitted_amount(form_data)
                currency = form_data["onetime_currency"]
                if currency not in RECURRING_CURRENCIES:
                    raise ValueError("Select a valid currency.")
                recipient = _recipient_payload(
                    recipients, form_data["onetime_recipient"]
                )
                api = RefinanceAPI(token=None)
                response = api.http(
                    "POST",
                    "donations",
                    data={
                        "amount": str(amount),
                        "currency": currency,
                        "comment": form_data["comment"],
                        **recipient,
                    },
                )
                result = response.json()
                payment_url = result.get("payment_url")
                if payment_url:
                    return redirect(payment_url)

                return redirect(
                    url_for("donation.pending", deposit_uuid=result["deposit_uuid"])
                )
            except ValueError as e:
                flash(str(e), "error")
            except ApplicationError as e:
                flash(f"Could not create donation: {e}", "error")

    return render_template(
        "donation/donate.jinja2",
        form_data=form_data,
        donation_presets=DONATION_PRESET_AMOUNTS,
        donation_min_amount=Config.DONATION_MIN_AMOUNT,
        donation_max_amount=Config.DONATION_MAX_AMOUNT,
        stripe_configured=Config.STRIPE_CONFIGURED,
        recipients=recipients,
    )


@donation_bp.route("/pending/<string:deposit_uuid>")
def pending(deposit_uuid: str):
    api = RefinanceAPI(token=None)
    try:
        result = api.http("GET", f"donations/{deposit_uuid}").json()
    except ApplicationError:
        flash("Donation not found.", "error")
        return redirect(url_for("donation.donate"))

    return render_template("donation/pending.jinja2", donation=result)


@donation_bp.route("/subscribed")
def subscribed():
    stripe_session_id = (request.args.get("stripe_session_id") or "").strip()
    portal_url = None
    if stripe_session_id:
        try:
            api = RefinanceAPI(token=None)
            api.http(
                "POST",
                "donations/subscribe/sync",
                params={"checkout_session_id": stripe_session_id},
            )
        except ApplicationError as e:
            flash(f"Could not confirm subscription: {e}", "error")
        except Exception as e:
            flash(f"Could not confirm subscription: {e}", "error")
        try:
            api = RefinanceAPI(token=None)
            result = api.http(
                "GET",
                "donations/portal",
                params={
                    "checkout_session_id": stripe_session_id,
                    "return_url": url_for("donation.donate", _external=True),
                },
            ).json()
            portal_url = result.get("portal_url")
        except Exception:
            pass  # Portal URL is optional; don't fail the page

    return render_template("donation/subscribed.jinja2", portal_url=portal_url)
