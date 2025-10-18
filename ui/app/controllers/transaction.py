from app.external.refinance import get_refinance_api_client
from app.middlewares.auth import token_required
from app.schemas import Tag, Transaction, TransactionStatus
from flask import Blueprint, jsonify, redirect, render_template, request, url_for
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
    currency = StringField(
        "Currency",
        validators=[DataRequired()],
        description="Any string, but prefer <a href='https://en.wikipedia.org/wiki/ISO_4217#Active_codes_(list_one)'>ISO 4217</a>. Case insensitive.",
        render_kw={"placeholder": "GEL", "class": "small"},
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
    currency = StringField(
        "Currency",
        render_kw={"placeholder": "GEL", "class": "small"},
    )
    status = SelectField(
        "Status", choices=[("", "")] + [(e.value, e.value) for e in TransactionStatus]
    )
    submit = SubmitField("Search")


def _get_treasury_choices():
    """Fetch treasuries and return select choices"""
    api = get_refinance_api_client()
    items = api.http("GET", "treasuries").json().get("items", [])
    return [(0, "")] + [(t["id"], t["name"]) for t in items]


@transaction_bp.route("/")
@token_required
def list():
    # Get the current page and limit from query parameters, defaulting to page 1 and 10 items per page.
    page = request.args.get("page", 1, type=int)
    limit = request.args.get("limit", 20, type=int)
    skip = (page - 1) * limit

    filter_form = TransactionFilterForm(request.args)
    # leave only non-empty filters
    filters = {
        key: value
        for (key, value) in filter_form.data.items()
        if value not in (None, "")
    }

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
