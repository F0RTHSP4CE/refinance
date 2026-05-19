from app.config import Config
from app.exceptions.base import ApplicationError
from app.external.refinance import RefinanceAPI
from flask import Blueprint, flash, redirect, render_template, url_for
from flask_wtf import FlaskForm
from wtforms import FloatField, SelectField, StringField, SubmitField
from wtforms.validators import DataRequired, NumberRange, Optional

donation_bp = Blueprint("donation", __name__)


class DonationForm(FlaskForm):
    amount = FloatField(
        "Amount",
        validators=[DataRequired(), NumberRange(min=0.01)],
        render_kw={"placeholder": "10.00", "class": "small"},
    )
    currency = SelectField(
        "Currency",
        choices=Config.CURRENCY_CHOICES,
        default=Config.PREFERRED_CURRENCY,
        validate_choice=False,
        validators=[DataRequired()],
    )
    comment = StringField(
        "Comment",
        validators=[Optional()],
        render_kw={"placeholder": "optional message"},
    )
    submit = SubmitField("Donate")


@donation_bp.route("/", methods=["GET", "POST"])
def donate():
    form = DonationForm()

    if form.validate_on_submit():
        api = RefinanceAPI(token=None)
        try:
            response = api.http(
                "POST",
                "donations",
                data={
                    "amount": form.amount.data,
                    "currency": (form.currency.data or "").strip().upper(),
                    "comment": form.comment.data or "",
                },
            )
            result = response.json()
            return redirect(
                url_for("donation.pending", deposit_uuid=result["deposit_uuid"])
            )
        except ApplicationError as e:
            flash(f"Could not create donation: {e}", "error")

    return render_template("donation/donate.jinja2", form=form)


@donation_bp.route("/pending/<string:deposit_uuid>")
def pending(deposit_uuid: str):
    api = RefinanceAPI(token=None)
    try:
        result = api.http("GET", f"donations/{deposit_uuid}").json()
    except ApplicationError:
        flash("Donation not found.", "error")
        return redirect(url_for("donation.donate"))

    return render_template("donation/pending.jinja2", donation=result)
