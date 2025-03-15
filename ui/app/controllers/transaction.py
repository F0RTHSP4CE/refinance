from app.external.refinance import get_refinance_api_client
from app.middlewares.auth import token_required
from app.schemas import Transaction
from flask import Blueprint, jsonify, redirect, render_template, request, url_for
from flask_wtf import FlaskForm
from wtforms import FloatField, IntegerField, SelectField, StringField, SubmitField
from wtforms.validators import DataRequired, NumberRange

transaction_bp = Blueprint("transaction", __name__)


class TransactionForm(FlaskForm):
    from_entity_name = StringField("From")
    to_entity_name = StringField("To")
    from_entity_id = IntegerField("", validators=[DataRequired(), NumberRange(min=1)])
    to_entity_id = IntegerField("", validators=[DataRequired(), NumberRange(min=1)])
    comment = StringField("Comment")
    amount = FloatField(
        "Amount",
        validators=[DataRequired()],
        render_kw={"placeholder": "10.00"},
    )
    currency = StringField(
        "Currency",
        validators=[DataRequired()],
        description="Any string, but prefer <a href='https://en.wikipedia.org/wiki/ISO_4217#Active_codes_(list_one)'>ISO 4217</a>. Case insensitive.",
        render_kw={"placeholder": "GEL, USD, DOGE"},
    )
    submit = SubmitField("Submit")


class DeleteForm(FlaskForm):
    delete = SubmitField("Delete")


class ConfirmForm(FlaskForm):
    confirm = SubmitField("Confirm")


@transaction_bp.route("/")
@token_required
def list():
    api = get_refinance_api_client()
    return render_template(
        "transaction/list.jinja2",
        transactions=[
            Transaction(**x) for x in api.http("GET", "transactions").json()["items"]
        ],
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
    form = TransactionForm()
    if form.validate_on_submit():
        api = get_refinance_api_client()
        tx = api.http("POST", "transactions", data=form.data)
        if tx.status_code == 200:
            return redirect(url_for("transaction.detail", id=tx.json()["id"]))
    return render_template("transaction/add.jinja2", form=form)


@transaction_bp.route("/<int:id>/edit", methods=["GET", "POST"])
@token_required
def edit(id):
    api = get_refinance_api_client()
    transaction = Transaction(**api.http("GET", f"transactions/{id}").json())
    form = TransactionForm(**transaction.__dict__)
    if form.validate_on_submit():
        form.populate_obj(transaction)
        api.http("PATCH", f"transactions/{id}", data=form.data)
        return redirect(url_for("transaction.detail", id=id))
    return render_template(
        "transaction/edit.jinja2", form=form, transaction=transaction
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


@transaction_bp.route("/<int:id>/confirm", methods=["GET", "POST"])
@token_required
def confirm(id):
    api = get_refinance_api_client()
    transaction = Transaction(**api.http("GET", f"transactions/{id}").json())
    form = ConfirmForm()
    if form.validate_on_submit():
        api.http("PATCH", f"transactions/{id}", data={"confirmed": True})
        return redirect(url_for("transaction.detail", id=id))
    return render_template(
        "transaction/confirm.jinja2", form=form, transaction=transaction
    )
