from decimal import Decimal, InvalidOperation

from app.external.refinance import get_refinance_api_client
from app.middlewares.auth import token_required
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_wtf import FlaskForm
from wtforms import (
    BooleanField,
    DecimalField,
    SelectField,
    SelectMultipleField,
    SubmitField,
)
from wtforms.validators import DataRequired

fortune_bp = Blueprint("fortune", __name__)


class FortunePlayForm(FlaskForm):
    stake = DecimalField("Stake", validators=[DataRequired()], places=2)
    currency = SelectField("Currency", choices=[], validators=[DataRequired()])
    boosted = BooleanField("Boost probability")
    selected_tiles = SelectMultipleField("Tiles", coerce=int, choices=[])
    submit = SubmitField("Reveal fortune")


def _is_cent_amount(value: Decimal) -> bool:
    try:
        return value.is_finite() and value == value.quantize(Decimal("0.01"))
    except InvalidOperation:
        return False


def _max_allowed_stake_for_currency(
    rules: dict, max_allowed_by_currency: dict, currency: str
) -> Decimal:
    selected_currency = str(currency or rules.get("currency") or "").lower()
    raw_limit = Decimal(
        str(
            max_allowed_by_currency.get(
                selected_currency, rules.get("max_stake", "0.00")
            )
        )
    )
    rule_limit = Decimal(str(rules.get("max_stake", "0.00")))
    return min(rule_limit, raw_limit)


@fortune_bp.route("/")
@token_required
def start():
    api = get_refinance_api_client()
    game = api.http("POST", "fortune/games").json()
    return redirect(url_for("fortune.detail", game_id=game["id"]))


@fortune_bp.route("/<int:game_id>", methods=["GET", "POST"])
@token_required
def detail(game_id: int):
    api = get_refinance_api_client()
    game = api.http("GET", f"fortune/games/{game_id}").json()
    rules = game["rules"]

    if game["status"] == "settled":
        return render_template("fortune/detail.jinja2", game=game, form=None)

    max_allowed_by_currency = {
        str(currency).lower(): Decimal(str(amount))
        for currency, amount in (game.get("max_allowed_stakes") or {}).items()
    }

    form = FortunePlayForm()
    currencies = rules.get("currencies", [rules["currency"]])
    form.currency.choices = [
        (str(currency).lower(), str(currency).upper()) for currency in currencies
    ]
    form.selected_tiles.choices = [
        (tile, str(tile)) for tile in range(1, int(rules["total_tiles"]) + 1)
    ]
    if request.method == "GET":
        form.stake.data = Decimal(str(rules["stake_presets"][0]))
        form.currency.data = str(rules["currency"]).lower()

    if form.validate_on_submit():
        stake = form.stake.data
        required_count = int(
            rules[
                (
                    "boosted_player_tile_count"
                    if form.boosted.data
                    else "player_tile_count"
                )
            ]
        )
        max_allowed = _max_allowed_stake_for_currency(
            rules, max_allowed_by_currency, form.currency.data
        )
        if not _is_cent_amount(stake):
            flash("Stake must use whole cents.", "error")
        elif stake < Decimal(str(rules["min_stake"])) or stake > Decimal(
            str(rules["max_stake"])
        ):
            flash(
                f"Stake must be between {rules['min_stake']} and "
                f"{rules['max_stake']} {str(rules['currency']).upper()}.",
                "error",
            )
        elif stake > max_allowed:
            flash(
                f"Stake exceeds the fortune balance; maximum is "
                f"{max_allowed:.2f} {str(form.currency.data).upper()}.",
                "error",
            )
        elif (
            len(form.selected_tiles.data) != required_count
            or len(set(form.selected_tiles.data)) != required_count
        ):
            flash(f"Select exactly {required_count} unique tiles.", "error")
        else:
            api.http(
                "POST",
                f"fortune/games/{game_id}/play",
                data={
                    "stake": str(stake),
                    "currency": form.currency.data,
                    "boosted": bool(form.boosted.data),
                    "selected_tiles": form.selected_tiles.data,
                },
            )
            return redirect(url_for("fortune.detail", game_id=game_id))
    elif request.method == "POST":
        flash("Check the stake and selected tiles.", "error")

    return render_template("fortune/detail.jinja2", game=game, form=form)
