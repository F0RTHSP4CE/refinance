from decimal import Decimal

from app.external.refinance import get_refinance_api_client
from app.middlewares.auth import token_required
from app.schemas import Invoice, InvoiceStatus, Tag, Transaction, TransactionStatus
from flask import Blueprint, redirect, render_template, request, url_for
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

invoice_bp = Blueprint("invoice", __name__)


class InvoiceForm(FlaskForm):
    from_entity_name = StringField("From")
    from_entity_id = IntegerField("", validators=[DataRequired(), NumberRange(min=1)])
    to_entity_name = StringField("To")
    to_entity_id = IntegerField("", validators=[DataRequired(), NumberRange(min=1)])
    comment = StringField("Comment")

    amount_1 = FloatField(
        "Amount 1",
        validators=[DataRequired(), NumberRange(min=0.01)],
        render_kw={"placeholder": "10.00", "class": "small"},
    )
    currency_1 = SelectField(
        "Currency 1",
        choices=[("GEL", "GEL"), ("USD", "USD"), ("EUR", "EUR")],
        validators=[DataRequired()],
    )
    amount_2 = FloatField(
        "Amount 2",
        validators=[Optional(), NumberRange(min=0.01)],
        render_kw={"placeholder": "27.00", "class": "small"},
    )
    currency_2 = SelectField(
        "Currency 2",
        choices=[("GEL", "GEL"), ("USD", "USD"), ("EUR", "EUR")],
        validators=[Optional()],
    )
    amount_3 = FloatField(
        "Amount 3",
        validators=[Optional(), NumberRange(min=0.01)],
        render_kw={"placeholder": "5.00", "class": "small"},
    )
    currency_3 = SelectField(
        "Currency 3",
        choices=[("GEL", "GEL"), ("USD", "USD"), ("EUR", "EUR")],
        validators=[Optional()],
    )

    tag_ids = SelectMultipleField("Tags", coerce=int, choices=[])
    submit = SubmitField("Submit")


class InvoicePayForm(FlaskForm):
    invoice_id = HiddenField("")
    from_entity_id = HiddenField("")
    to_entity_id = HiddenField("")
    amount = FloatField(
        "Amount",
        validators=[DataRequired(), NumberRange(min=0.01)],
        render_kw={"placeholder": "10.00", "class": "small"},
    )
    currency = SelectField("Currency", choices=[], validators=[DataRequired()])
    status = SelectField(
        "Status",
        choices=[(e.value, e.value) for e in TransactionStatus],
        default=TransactionStatus.COMPLETED.value,
    )
    comment = StringField("Comment")
    submit = SubmitField("Pay")


class InvoiceFilterForm(FlaskForm):
    entity_name = StringField("Entity")
    entity_id = IntegerField("", validators=[Optional(), NumberRange(min=1)])
    from_entity_name = StringField("From")
    from_entity_id = IntegerField("", validators=[Optional(), NumberRange(min=1)])
    to_entity_name = StringField("To")
    to_entity_id = IntegerField("", validators=[Optional(), NumberRange(min=1)])
    actor_entity_name = StringField("Actor")
    actor_entity_id = IntegerField("", validators=[Optional(), NumberRange(min=1)])
    status = SelectField(
        "Status",
        choices=[("", "")] + [(e.value, e.value) for e in InvoiceStatus],
    )
    submit = SubmitField("Search")


class DeleteForm(FlaskForm):
    delete = SubmitField("Delete")


def _build_amounts_from_form(form: InvoiceForm) -> list[dict[str, str]]:
    amounts = []
    for amount_field, currency_field in (
        (form.amount_1, form.currency_1),
        (form.amount_2, form.currency_2),
        (form.amount_3, form.currency_3),
    ):
        amount = amount_field.data
        currency = currency_field.data
        if amount is None:
            continue
        if not currency:
            continue
        value = Decimal(str(amount)).quantize(Decimal("0.01"))
        amounts.append({"currency": currency.lower(), "amount": format(value, "f")})
    return amounts


def _populate_amount_fields(form: InvoiceForm, amounts: list[dict]) -> None:
    slots = [
        (form.amount_1, form.currency_1),
        (form.amount_2, form.currency_2),
        (form.amount_3, form.currency_3),
    ]
    for slot, entry in zip(slots, amounts):
        amount_field, currency_field = slot
        amount_field.data = float(entry.get("amount"))
        currency_field.data = str(entry.get("currency", "")).upper()


@invoice_bp.route("/")
@token_required
def list():
    page = request.args.get("page", 1, type=int)
    limit = request.args.get("limit", 20, type=int)
    skip = (page - 1) * limit

    filter_form = InvoiceFilterForm(request.args)
    filters = {}
    for key, value in filter_form.data.items():
        if value not in (None, ""):
            filters[key] = value

    api = get_refinance_api_client()
    response = api.http(
        "GET", "invoices", params={"skip": skip, "limit": limit, **filters}
    ).json()
    invoices = [Invoice(**x) for x in response["items"]]
    total = response["total"]

    return render_template(
        "invoice/list.jinja2",
        invoices=invoices,
        total=total,
        page=page,
        limit=limit,
        filter_form=filter_form,
    )


@invoice_bp.route("/add", methods=["GET", "POST"])
@token_required
def add():
    api = get_refinance_api_client()
    form = InvoiceForm()
    all_tags = [Tag(**x) for x in api.http("GET", "tags").json()["items"]]
    form.tag_ids.choices = [(tag.id, tag.name) for tag in all_tags]

    if form.validate_on_submit():
        data = {
            "from_entity_id": form.from_entity_id.data,
            "to_entity_id": form.to_entity_id.data,
            "comment": form.comment.data,
            "amounts": _build_amounts_from_form(form),
            "tag_ids": form.tag_ids.data,
        }
        invoice = api.http("POST", "invoices", data=data).json()
        return redirect(url_for("invoice.detail", id=invoice["id"]))

    return render_template("invoice/add.jinja2", form=form, all_tags=all_tags)


@invoice_bp.route("/<int:id>")
@token_required
def detail(id):
    api = get_refinance_api_client()
    invoice = Invoice(**api.http("GET", f"invoices/{id}").json())
    transaction = None
    if invoice.transaction_id:
        transaction = Transaction(
            **api.http("GET", f"transactions/{invoice.transaction_id}").json()
        )
    return render_template(
        "invoice/detail.jinja2",
        invoice=invoice,
        transaction=transaction,
    )


@invoice_bp.route("/<int:id>/edit", methods=["GET", "POST"])
@token_required
def edit(id):
    api = get_refinance_api_client()
    invoice_data = api.http("GET", f"invoices/{id}").json()
    invoice = Invoice(**invoice_data)

    form = InvoiceForm(data=invoice_data)
    _populate_amount_fields(form, invoice_data.get("amounts", []))

    all_tags = [Tag(**x) for x in api.http("GET", "tags").json()["items"]]
    form.tag_ids.choices = [(tag.id, tag.name) for tag in all_tags]
    form.tag_ids.data = [tag["id"] for tag in invoice_data.get("tags", [])]

    if form.validate_on_submit():
        data = {
            "comment": form.comment.data,
            "amounts": _build_amounts_from_form(form),
            "tag_ids": form.tag_ids.data,
        }
        api.http("PATCH", f"invoices/{id}", data=data)
        return redirect(url_for("invoice.detail", id=id))

    return render_template(
        "invoice/edit.jinja2",
        invoice=invoice,
        form=form,
        all_tags=all_tags,
    )


@invoice_bp.route("/<int:id>/pay", methods=["GET", "POST"])
@token_required
def pay(id):
    api = get_refinance_api_client()
    invoice_data = api.http("GET", f"invoices/{id}").json()
    invoice = Invoice(**invoice_data)
    amounts = invoice_data.get("amounts", [])

    form = InvoicePayForm()
    form.invoice_id.data = str(invoice.id)
    form.from_entity_id.data = str(invoice.from_entity_id)
    form.to_entity_id.data = str(invoice.to_entity_id)
    form.currency.choices = [
        (a["currency"].upper(), a["currency"].upper()) for a in amounts
    ]

    if form.currency.data is None and amounts:
        form.currency.data = amounts[0]["currency"].upper()
    if form.amount.data is None and amounts:
        form.amount.data = float(amounts[0]["amount"])

    if form.validate_on_submit():
        data = {
            "from_entity_id": int(form.from_entity_id.data),
            "to_entity_id": int(form.to_entity_id.data),
            "amount": form.amount.data,
            "currency": form.currency.data.lower(),
            "status": form.status.data,
            "comment": form.comment.data,
            "invoice_id": invoice.id,
        }
        tx = api.http("POST", "transactions", data=data).json()
        return redirect(url_for("transaction.detail", id=tx["id"]))

    return render_template(
        "invoice/pay.jinja2",
        invoice=invoice,
        form=form,
        amounts=amounts,
    )
