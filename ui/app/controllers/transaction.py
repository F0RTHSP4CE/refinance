import calendar
from datetime import date, datetime
from decimal import Decimal
from typing import Dict, List

from app.config import Config
from app.external.refinance import get_refinance_api_client
from app.middlewares.auth import token_required
from app.schemas import Tag, Transaction, TransactionStatus
from flask import Blueprint, g, jsonify, redirect, render_template, request, url_for
from flask_wtf import FlaskForm
from wtforms import (
    FloatField,
    IntegerField,
    SelectField,
    SelectMultipleField,
    StringField,
    SubmitField,
)
from wtforms.validators import DataRequired, NumberRange, Optional

transaction_bp = Blueprint("transaction", __name__)


class TransactionForm(FlaskForm):
    from_entity_name = StringField("From")
    to_entity_name = StringField("To")
    from_entity_id = IntegerField("", validators=[DataRequired(), NumberRange(min=1)])
    to_entity_id = IntegerField("", validators=[DataRequired(), NumberRange(min=1)])
    comment = StringField("Comment")
    amount = FloatField(
        "Amount",
        validators=[
            DataRequired(),
            NumberRange(min=0.01, message="Amount must be greater than 0"),
        ],
        render_kw={"placeholder": "10.00", "class": "small"},
    )
    currency = SelectField(
        "Currency",
        choices=[("GEL", "GEL"), ("USD", "USD"), ("EUR", "EUR")],
        default="GEL",
        validators=[DataRequired()],
    )
    status = SelectField(
        "Status",
        choices=[(e.value, e.value) for e in TransactionStatus],
        default=TransactionStatus.DRAFT.value,
        description="Draft — can be edited. Completed — confirmed and executed, cannot be edited after confirmation.",
    )
    # Treasury dropdowns
    from_treasury_id = SelectField("From Treasury", coerce=int, choices=[], default=0)
    to_treasury_id = SelectField(
        "To Treasury",
        coerce=int,
        choices=[],
        default=0,
        description="For deposits/withdrawals only. Physical money source and destination.",
    )

    tag_ids = SelectMultipleField(
        "Tags", coerce=int, choices=[], description="Select tags for this transaction"
    )
    submit = SubmitField("Submit")


class DeleteForm(FlaskForm):
    delete = SubmitField("Delete")


class ConfirmForm(FlaskForm):
    confirm = SubmitField("Confirm")


class TransactionFilterForm(FlaskForm):
    entity_name = StringField("Entity (From/To)")
    entity_id = IntegerField("", validators=[NumberRange(min=1)])
    actor_entity_name = StringField("Actor")
    actor_entity_id = IntegerField("", validators=[NumberRange(min=1)])
    from_entity_name = StringField("From")
    from_entity_id = IntegerField("", validators=[DataRequired(), NumberRange(min=1)])
    to_entity_name = StringField("To")
    to_entity_id = IntegerField("", validators=[DataRequired(), NumberRange(min=1)])
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
        "Status", choices=[("", "")] + [(e.value, e.value) for e in TransactionStatus]
    )
    treasury_id = SelectField(
        "Treasury",
        coerce=int,
        choices=[],
        default=0,
        validators=[Optional()],
    )
    submit = SubmitField("Search")


def _get_treasury_choices():
    """Fetch treasuries and return select choices"""
    api = get_refinance_api_client()
    items = api.http("GET", "treasuries").json().get("items", [])
    return [(0, "")] + [(t["id"], t["name"]) for t in items]


DEPOSIT_TAG_ID = Config.TAG_IDS["deposit"]
WITHDRAWAL_TAG_ID = Config.TAG_IDS["withdrawal"]
FEE_TAG_ID = Config.TAG_IDS["fee"]


def _get_active_treasuries(api):
    """Fetch active treasuries"""
    return (
        api.http("GET", "treasuries", params={"active": "true"}).json().get("items", [])
    )


def _get_entities_by_tag_id(api, tag_id: int | None, active_only: bool = False):
    if not tag_id:
        return []
    params = {"tags_ids": tag_id, "limit": 500}
    if active_only:
        params["active"] = "true"
    return api.http("GET", "entities", params=params).json().get("items", [])


def _build_resident_fees(api):
    raw_fees = api.http("GET", "resident_fees").json()
    fees = []
    for data in raw_fees:
        converted = []
        for f in data.get("fees", []):
            raw_amounts = f.get("amounts", {})
            amounts = {
                currency: Decimal(str(value)) for currency, value in raw_amounts.items()
            }
            total_usd_raw = f.get("total_usd", 0)
            total_usd = Decimal(str(total_usd_raw or 0))
            converted.append(
                {
                    "year": f["year"],
                    "month": f["month"],
                    "amounts": amounts,
                    "total_usd": total_usd,
                }
            )
        data["fees"] = converted
        fees.append(data)

    timeline_set = set()
    for rf in fees:
        for f in rf.get("fees", []):
            timeline_set.add((f["year"], f["month"]))
    timeline = sorted(timeline_set)

    for rf in fees:
        fee_map = {(f["year"], f["month"]): f for f in rf.get("fees", [])}
        rf["fees"] = []
        for y, m in timeline:
            existing = fee_map.get((y, m))
            if existing is not None:
                rf["fees"].append(existing)
            else:
                rf["fees"].append(
                    {
                        "year": y,
                        "month": m,
                        "amounts": {},
                        "total_usd": Decimal("0"),
                    }
                )

    current_date = datetime.utcnow()
    return fees, current_date.month, current_date.year


@transaction_bp.route("/")
@token_required
def list():
    # Get the current page and limit from query parameters, defaulting to page 1 and 10 items per page.
    page = request.args.get("page", 1, type=int)
    limit = request.args.get("limit", 20, type=int)
    skip = (page - 1) * limit

    filter_form = TransactionFilterForm(request.args)

    # populate treasury dropdown for filtering
    treasury_choices = _get_treasury_choices()
    filter_form.treasury_id.choices = treasury_choices  # type: ignore
    # leave only non-empty filters
    filters = {}
    for key, value in filter_form.data.items():
        if key == "treasury_id":
            # treat 0 as "no filter" for select field
            if value and value != 0:
                filters[key] = value
        elif value not in (None, ""):
            filters[key] = value

    api = get_refinance_api_client()
    # Pass skip and limit to the FastAPI endpoint
    response = api.http(
        "GET", "transactions", params={"skip": skip, "limit": limit, **filters}
    ).json()

    # Extract transactions and pagination details from the API response
    transactions = [Transaction(**x) for x in response["items"]]
    total = response["total"]

    return render_template(
        "transaction/list.jinja2",
        transactions=transactions,
        total=total,
        page=page,
        limit=limit,
        filter_form=filter_form,
    )


@transaction_bp.route("/<int:id>")
@token_required
def detail(id):
    api = get_refinance_api_client()
    return render_template(
        "transaction/detail.jinja2",
        transaction=Transaction(**api.http("GET", f"transactions/{id}").json()),
    )


@transaction_bp.route("/add", methods=["GET", "POST"])
@token_required
def add():
    api = get_refinance_api_client()
    form = TransactionForm()

    # populate treasury dropdowns
    choices = _get_treasury_choices()
    form.from_treasury_id.choices = choices  # type: ignore
    form.to_treasury_id.choices = choices  # type: ignore

    # populate tag choices
    all_tags = [Tag(**x) for x in api.http("GET", "tags").json()["items"]]
    form.tag_ids.choices = [(tag.id, tag.name) for tag in all_tags]

    if form.validate_on_submit():
        data = form.data.copy()
        data.pop("csrf_token", None)
        if not data.get("from_treasury_id"):
            data["from_treasury_id"] = None
        if not data.get("to_treasury_id"):
            data["to_treasury_id"] = None
        tx = api.http("POST", "transactions", data=data)
        if tx.status_code == 200:
            return redirect(url_for("transaction.detail", id=tx.json()["id"]))
    return render_template("transaction/add.jinja2", form=form, all_tags=all_tags)


@transaction_bp.route("/shortcuts/deposit", methods=["GET", "POST"])
@token_required
def shortcut_deposit():
    api = get_refinance_api_client()
    deposit_entities = _get_entities_by_tag_id(api, DEPOSIT_TAG_ID, active_only=True)
    treasuries = _get_active_treasuries(api)

    if request.method == "POST":
        to_treasury_id = request.form.get("to_treasury_id")
        data = {
            "from_entity_id": int(request.form["from_entity_id"]),
            "to_entity_id": int(request.form["to_entity_id"]),
            "amount": float(request.form["amount"]),
            "currency": request.form["currency"],
            "comment": request.form.get("comment", ""),
            "status": "draft",
            "tag_ids": [DEPOSIT_TAG_ID],
            "to_treasury_id": int(to_treasury_id) if to_treasury_id else None,
        }
        tx = api.http("POST", "transactions", data=data)
        return redirect(url_for("transaction.detail", id=tx.json()["id"]))

    return render_template(
        "transaction/shortcuts_deposit.jinja2",
        deposit_entities=deposit_entities,
        treasuries=treasuries,
    )


@transaction_bp.route("/shortcuts/pay", methods=["GET", "POST"])
@token_required
def shortcut_pay():
    api = get_refinance_api_client()
    if request.method == "POST":
        data = {
            "from_entity_id": int(request.form["from_entity_id"]),
            "to_entity_id": int(request.form["to_entity_id"]),
            "amount": float(request.form["amount"]),
            "currency": request.form["currency"],
            "comment": request.form.get("comment", ""),
            "status": "draft",
            "tag_ids": [],
        }
        tx = api.http("POST", "transactions", data=data)
        return redirect(url_for("transaction.detail", id=tx.json()["id"]))

    return render_template("transaction/shortcuts_pay.jinja2")


@transaction_bp.route("/shortcuts/request", methods=["GET", "POST"])
@token_required
def shortcut_request():
    api = get_refinance_api_client()
    if request.method == "POST":
        data = {
            "from_entity_id": int(request.form["from_entity_id"]),
            "to_entity_id": int(request.form["to_entity_id"]),
            "amount": float(request.form["amount"]),
            "currency": request.form["currency"],
            "comment": request.form.get("comment", ""),
            "status": "draft",
            "tag_ids": [],
        }
        tx = api.http("POST", "transactions", data=data)
        return redirect(url_for("transaction.detail", id=tx.json()["id"]))

    return render_template("transaction/shortcuts_request.jinja2")


@transaction_bp.route("/shortcuts/monthly-fee", methods=["GET", "POST"])
@token_required
def shortcut_monthly_fee():
    api = get_refinance_api_client()
    fee_presets = Config.DEFAULT_MONTHLY_FEE_PRESETS

    def _build_fee_presets_list(presets: dict) -> List[Dict[str, float | str]]:
        items: List[Dict[str, float | str]] = []
        for group_key, currencies in presets.items():
            if not isinstance(currencies, dict):
                continue
            group_label = str(group_key).replace("_", " ").title()
            for currency, amount in currencies.items():
                if amount is None:
                    continue
                amount_value = float(amount)
                items.append(
                    {
                        "value": f"{amount_value}_{str(currency).upper()}",
                        "label": f"{amount_value:g} {str(currency).upper()} — {group_label}",
                        "amount": amount_value,
                        "currency": str(currency).upper(),
                    }
                )
        return items

    fee_preset_options = _build_fee_presets_list(fee_presets)
    preset_map = {
        option["value"]: (option["amount"], option["currency"])
        for option in fee_preset_options
    }

    def _get_default_fee_preset(actor_entity, balance, presets: dict) -> str:
        def _first_available_preset() -> str:
            for group in presets.keys():
                group_presets = presets.get(group) or {}
                for currency in group_presets.keys():
                    amount = group_presets.get(currency)
                    if amount is not None:
                        return f"{float(amount)}_{currency.upper()}"
            return "custom"

        if not actor_entity:
            return _first_available_preset()

        tags = actor_entity.get("tags") or []
        tag_ids = {
            tag.get("id")
            for tag in tags
            if isinstance(tag, dict) and tag.get("id") is not None
        }
        is_resident = Config.TAG_IDS["resident"] in tag_ids
        is_member = Config.TAG_IDS["member"] in tag_ids

        completed = (balance or {}).get("completed") or {}
        normalized_balances: dict[str, float] = {}
        for currency, amount in completed.items():
            if amount is None:
                continue
            try:
                normalized_balances[str(currency).lower()] = float(amount)
            except (TypeError, ValueError):
                continue

        def _has_funds(currency: str, required: float) -> bool:
            return normalized_balances.get(currency.lower(), 0.0) >= required

        def _choose_for(group: str) -> str | None:
            group_presets = presets.get(group) or {}
            for currency in group_presets.keys():
                amount = group_presets.get(currency)
                if amount is not None:
                    return f"{float(amount)}_{currency.upper()}"
            return None

        if is_resident:
            return _choose_for("resident") or _first_available_preset()

        if is_member:
            return _choose_for("member") or _first_available_preset()

        return _first_available_preset()

    today = date.today()

    def _month_label(offset: int) -> str:
        base_index = (today.year * 12 + (today.month - 1)) + offset
        year = base_index // 12
        month = base_index % 12 + 1
        return f"fee {calendar.month_abbr[month].lower()} {year}"

    comment_options = [_month_label(offset) for offset in range(-6, 7)]
    default_comment = _month_label(0)

    fee_row = None
    fees, current_month, current_year = _build_resident_fees(api)
    actor_id = g.actor_entity.get("id") if g.actor_entity else None
    if actor_id is not None:
        for rf in fees:
            entity_data = rf.get("entity") or {}
            if entity_data.get("id") == actor_id or rf.get("entity_id") == actor_id:
                fee_row = rf
                break

    if request.method == "POST":
        preset = request.form.get("fee_preset", "70_GEL")
        if preset == "custom":
            amount = float(request.form["custom_amount"])
            currency = request.form["custom_currency"]
        else:
            amount, currency = preset_map[preset]

        data = {
            "from_entity_id": int(request.form["from_entity_id"]),
            "to_entity_id": int(request.form["to_entity_id"]),
            "amount": amount,
            "currency": currency,
            "comment": request.form.get("comment", ""),
            "status": "draft",
            "tag_ids": [FEE_TAG_ID],
        }
        tx = api.http("POST", "transactions", data=data)
        return redirect(url_for("transaction.detail", id=tx.json()["id"]))

    default_fee_preset = _get_default_fee_preset(
        g.actor_entity if hasattr(g, "actor_entity") else None,
        g.actor_entity_balance if hasattr(g, "actor_entity_balance") else None,
        fee_presets,
    )

    return render_template(
        "transaction/shortcuts_monthly_fee.jinja2",
        comment_options=comment_options,
        default_comment=default_comment,
        default_fee_preset=default_fee_preset,
        fee_presets=fee_preset_options,
        fee_row=fee_row,
        current_month=current_month,
        current_year=current_year,
        f0_entity_id=Config.ENTITY_IDS["f0"],
    )


@transaction_bp.route("/shortcuts/withdraw", methods=["GET", "POST"])
@token_required
def shortcut_withdraw():
    api = get_refinance_api_client()
    withdrawal_entities = _get_entities_by_tag_id(api, WITHDRAWAL_TAG_ID)
    treasuries = _get_active_treasuries(api)

    if request.method == "POST":
        from_treasury_id = request.form.get("from_treasury_id")
        data = {
            "from_entity_id": int(request.form["from_entity_id"]),
            "to_entity_id": int(request.form["to_entity_id"]),
            "amount": float(request.form["amount"]),
            "currency": request.form["currency"],
            "comment": request.form.get("comment", ""),
            "status": "draft",
            "tag_ids": [WITHDRAWAL_TAG_ID],
            "from_treasury_id": int(from_treasury_id) if from_treasury_id else None,
        }
        tx = api.http("POST", "transactions", data=data)
        return redirect(url_for("transaction.detail", id=tx.json()["id"]))

    return render_template(
        "transaction/shortcuts_withdraw.jinja2",
        withdrawal_entities=withdrawal_entities,
        treasuries=treasuries,
    )


@transaction_bp.route("/shortcuts/fridge", methods=["GET", "POST"])
@token_required
def shortcut_fridge():
    api = get_refinance_api_client()
    preset_options: List[Dict[str, float | str]] = []
    for preset in Config.FRIDGE_PRESETS:
        amount = float(preset.get("amount", 0))
        currency = str(preset.get("currency", "")).upper()
        label = preset.get("label") or f"{amount:g} {currency}"
        preset_options.append(
            {
                "value": f"{amount}_{currency}",
                "label": label,
                "amount": amount,
                "currency": currency,
            }
        )
    preset_map = {
        option["value"]: (option["amount"], option["currency"])
        for option in preset_options
    }

    if request.method == "POST":
        preset = request.form.get("fee_preset", "5_GEL")
        if preset == "custom":
            amount = float(request.form["custom_amount"])
            currency = request.form["custom_currency"]
        else:
            amount, currency = preset_map[preset]

        data = {
            "from_entity_id": int(request.form["from_entity_id"]),
            "to_entity_id": int(request.form["to_entity_id"]),
            "amount": amount,
            "currency": currency,
            "comment": request.form.get("comment", ""),
            "status": "draft",
            "tag_ids": [],
        }
        tx = api.http("POST", "transactions", data=data)
        return redirect(url_for("transaction.detail", id=tx.json()["id"]))

    return render_template(
        "transaction/shortcuts_fridge.jinja2",
        fridge_entity_id=Config.ENTITY_IDS["fridge"],
        preset_options=preset_options,
    )


@transaction_bp.route("/shortcuts/coffee", methods=["GET", "POST"])
@token_required
def shortcut_coffee():
    api = get_refinance_api_client()
    preset_options: List[Dict[str, float | str]] = []
    for preset in Config.COFFEE_PRESETS:
        amount = float(preset.get("amount", 0))
        currency = str(preset.get("currency", "")).upper()
        label = preset.get("label") or f"{amount:g} {currency}"
        preset_options.append(
            {
                "value": f"{amount}_{currency}",
                "label": label,
                "amount": amount,
                "currency": currency,
            }
        )
    preset_map = {
        option["value"]: (option["amount"], option["currency"])
        for option in preset_options
    }

    if request.method == "POST":
        preset = request.form.get("fee_preset", "5_GEL")
        if preset == "custom":
            amount = float(request.form["custom_amount"])
            currency = request.form["custom_currency"]
        else:
            amount, currency = preset_map[preset]

        data = {
            "from_entity_id": int(request.form["from_entity_id"]),
            "to_entity_id": int(request.form["to_entity_id"]),
            "amount": amount,
            "currency": currency,
            "comment": request.form.get("comment", ""),
            "status": "draft",
            "tag_ids": [],
        }
        tx = api.http("POST", "transactions", data=data)
        return redirect(url_for("transaction.detail", id=tx.json()["id"]))

    return render_template(
        "transaction/shortcuts_coffee.jinja2",
        coffee_entity_id=Config.ENTITY_IDS["coffee"],
        preset_options=preset_options,
    )


@transaction_bp.route("/shortcuts/reimburse", methods=["GET", "POST"])
@token_required
def shortcut_reimburse():
    api = get_refinance_api_client()

    if request.method == "POST":
        data = {
            "from_entity_id": int(request.form["from_entity_id"]),
            "to_entity_id": int(request.form["to_entity_id"]),
            "amount": float(request.form["amount"]),
            "currency": request.form["currency"],
            "comment": request.form.get("comment", ""),
            "status": "draft",
            "tag_ids": [],
        }
        tx = api.http("POST", "transactions", data=data)
        return redirect(url_for("transaction.detail", id=tx.json()["id"]))

    return render_template(
        "transaction/shortcuts_reimburse.jinja2",
        fridge_entity_id=Config.ENTITY_IDS["fridge"],
        coffee_entity_id=Config.ENTITY_IDS["coffee"],
    )


@transaction_bp.route("/shortcuts/exchange")
@token_required
def shortcut_exchange():
    return redirect(url_for("exchange.index"))


@transaction_bp.route("/<int:id>/edit", methods=["GET", "POST"])
@token_required
def edit(id):
    api = get_refinance_api_client()
    transaction = Transaction(**api.http("GET", f"transactions/{id}").json())
    # initialize form with transaction data and treasury IDs
    init_data = {
        **transaction.__dict__,
        "from_treasury_id": transaction.from_treasury_id or 0,
        "to_treasury_id": transaction.to_treasury_id or 0,
        "tag_ids": [
            tag["id"] if isinstance(tag, dict) else tag.id for tag in transaction.tags
        ],
    }
    form = TransactionForm(data=init_data)

    # populate treasury dropdowns
    choices = _get_treasury_choices()
    form.from_treasury_id.choices = choices  # type: ignore
    form.to_treasury_id.choices = choices  # type: ignore

    # populate tag choices
    all_tags = [Tag(**x) for x in api.http("GET", "tags").json()["items"]]
    form.tag_ids.choices = [(tag.id, tag.name) for tag in all_tags]

    if form.validate_on_submit():
        data = form.data.copy()
        data.pop("csrf_token", None)
        if not data.get("from_treasury_id"):
            data["from_treasury_id"] = None
        if not data.get("to_treasury_id"):
            data["to_treasury_id"] = None
        api.http("PATCH", f"transactions/{id}", data=data)
        return redirect(url_for("transaction.detail", id=id))

    return render_template(
        "transaction/edit.jinja2",
        form=form,
        transaction=transaction,
        all_tags=all_tags,
    )


@transaction_bp.route("/<int:id>/delete", methods=["GET", "POST"])
@token_required
def delete(id):
    api = get_refinance_api_client()
    transaction = Transaction(**api.http("GET", f"transactions/{id}").json())
    form = DeleteForm()
    if form.validate_on_submit():
        api.http("DELETE", f"transactions/{id}")
        return redirect(url_for("transaction.list"))
    return render_template(
        "transaction/delete.jinja2", form=form, transaction=transaction
    )


@transaction_bp.route("/<int:id>/complete", methods=["GET", "POST"])
@token_required
def complete(id):
    api = get_refinance_api_client()
    transaction = Transaction(**api.http("GET", f"transactions/{id}").json())
    form = ConfirmForm()
    if form.validate_on_submit():
        api.http("PATCH", f"transactions/{id}", data={"status": "completed"})
        return redirect(url_for("transaction.detail", id=id))
    return render_template(
        "transaction/complete.jinja2", form=form, transaction=transaction
    )
