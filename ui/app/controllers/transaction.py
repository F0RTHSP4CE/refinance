from app.external.refinance import get_refinance_api_client
from app.middlewares.auth import token_required
from app.schemas import Transaction
from flask import Blueprint, redirect, render_template, url_for
from flask_wtf import FlaskForm
from wtforms import (
    BooleanField,
    FloatField,
    IntegerField,
    StringField,
    SubmitField,
)
from wtforms.validators import DataRequired

transaction_bp = Blueprint("transaction", __name__)


class TransactionForm(FlaskForm):
    amount = FloatField("Amount", validators=[DataRequired()])
    from_entity_id = IntegerField("From Entity ID", validators=[DataRequired()])
    to_entity_id = IntegerField("To Entity ID", validators=[DataRequired()])
    currency = StringField("Currency", validators=[DataRequired()])
    confirmed = BooleanField("Confirmed", default=False)
    comment = StringField("Comment")
    submit = SubmitField("Save")


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
        api.http("POST", "transactions", data=form.data)
        return redirect(url_for("transaction.list"))
    return render_template("transaction/add.jinja2", form=form)


@transaction_bp.route("/edit/<int:id>", methods=["GET", "POST"])
@token_required
def edit(id):
    api = get_refinance_api_client()
    transaction_data = api.http("GET", f"transactions/{id}").json()
    form = TransactionForm(obj=transaction_data)
    if form.validate_on_submit():
        form.populate_obj(transaction_data)
        api.http("PATCH", f"transactions/{id}", data=transaction_data)
        return redirect(url_for("transaction.detail", id=id))
    return render_template("transaction/edit.jinja2", form=form)
