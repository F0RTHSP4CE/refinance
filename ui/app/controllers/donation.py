from decimal import Decimal, InvalidOperation

from app.exceptions.base import ApplicationError
from app.external.refinance import RefinanceAPI
from flask import Blueprint, flash, redirect, render_template, request, url_for

donation_bp = Blueprint("donation", __name__)

DONATION_PRESET_AMOUNTS = ("10", "20", "50")
DONATION_CURRENCY = "GEL"
DONATION_CURRENCY_SYMBOL = "\u20be"


def _parse_amount(raw_amount: str) -> Decimal:
    normalized_amount = (
        raw_amount.upper()
        .replace(DONATION_CURRENCY, "")
        .replace(DONATION_CURRENCY_SYMBOL, "")
        .strip()
    )
    try:
        amount = Decimal(normalized_amount)
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("Enter a valid donation amount.") from exc

    if amount <= 0:
        raise ValueError("Donation amount must be greater than 0.")

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


@donation_bp.route("/", methods=["GET", "POST"])
def donate():
    form_data = {
        "comment": "",
        "preset_amount": "",
        "custom_amount": "",
    }

    if request.method == "POST":
        form_data = {
            "comment": (request.form.get("comment") or "").strip(),
            "preset_amount": (request.form.get("preset_amount") or "").strip(),
            "custom_amount": (request.form.get("custom_amount") or "").strip(),
        }

        try:
            amount = _submitted_amount(form_data)
            api = RefinanceAPI(token=None)
            response = api.http(
                "POST",
                "donations",
                data={
                    "amount": str(amount),
                    "currency": DONATION_CURRENCY,
                    "comment": form_data["comment"],
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
        donation_currency=DONATION_CURRENCY,
        donation_currency_symbol=DONATION_CURRENCY_SYMBOL,
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
