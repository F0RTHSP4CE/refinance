from app.external.refinance import get_refinance_api_client
from app.middlewares.auth import token_required
from app.schemas import Balance, Entity, Split, Transaction
from flask import Blueprint, redirect, render_template, request, url_for
from flask_wtf import FlaskForm
from wtforms import FloatField, FormField, IntegerField, StringField, SubmitField
from wtforms.validators import DataRequired, NumberRange, Optional

split_bp = Blueprint("split", __name__)


class SplitForm(FlaskForm):
    recipient_entity_name = StringField("Recipient")
    recipient_entity_id = IntegerField(
        "", validators=[DataRequired(), NumberRange(min=1)]
    )
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


class SplitAddParticipant(FlaskForm):
    entity_name = StringField("Entity")
    entity_id = IntegerField("", validators=[DataRequired(), NumberRange(min=1)])
    fixed_amount = FloatField(
        "Amount", render_kw={"placeholder": "optional"}, validators=[Optional()]
    )
    submit = SubmitField("Submit")


class DeleteForm(FlaskForm):
    delete = SubmitField("Delete")


class PerformForm(FlaskForm):
    perform = SubmitField("Perform")


@split_bp.route("/")
@token_required
def list():
    # Retrieve pagination parameters from the query string
    page = request.args.get("page", 1, type=int)
    limit = request.args.get("limit", 10, type=int)
    skip = (page - 1) * limit

    api = get_refinance_api_client()
    response = api.http("GET", "splits", params={"skip": skip, "limit": limit}).json()
    splits = [Split(**x) for x in response["items"]]
    total = response["total"]

    return render_template(
        "split/list.jinja2",
        splits=splits,
        total=total,
        page=page,
        limit=limit,
    )


@split_bp.route("/add", methods=["GET", "POST"])
@token_required
def add():
    form = SplitForm()
    if form.validate_on_submit():
        api = get_refinance_api_client()
        api.http("POST", "splits", data=form.data)
        return redirect(url_for("split.list"))
    return render_template("split/add.jinja2", form=form)


@split_bp.route("/<int:id>/edit", methods=["GET", "POST"])
@token_required
def edit(id):
    api = get_refinance_api_client()
    split = api.http("GET", f"splits/{id}").json()
    form = SplitForm(data=split)
    if form.validate_on_submit():
        api.http("PATCH", f"splits/{id}", data=form.data)
        return redirect(url_for("split.detail", id=id))

    return render_template(
        "split/edit.jinja2",
        split=split,
        form=form,
    )


@split_bp.route("/<int:id>")
@token_required
def detail(id):
    api = get_refinance_api_client()
    split = Split(**api.http("GET", f"splits/{id}").json())
    return render_template(
        "split/detail.jinja2",
        split=split,
    )


@split_bp.route("/<int:id>/delete", methods=["GET", "POST"])
@token_required
def delete(id):
    api = get_refinance_api_client()
    split = Split(**api.http("GET", f"splits/{id}").json())
    form = DeleteForm()
    if form.validate_on_submit():
        api.http("DELETE", f"splits/{id}")
        return redirect(url_for("split.list"))
    return render_template("split/delete.jinja2", form=form, split=split)


@split_bp.route("/<int:id>/perform", methods=["GET", "POST"])
@token_required
def perform(id):
    api = get_refinance_api_client()
    split = Split(**api.http("GET", f"splits/{id}").json())
    form = PerformForm()
    if form.validate_on_submit():
        api.http("POST", f"splits/{id}/perform")
        return redirect(url_for("split.detail", id=split.id))
    return render_template("split/perform.jinja2", form=form, split=split)


@split_bp.route("/<int:id>/participants/add", methods=["GET", "POST"])
@token_required
def add_participant(id):
    api = get_refinance_api_client()
    split = Split(**api.http("GET", f"splits/{id}").json())
    form = SplitAddParticipant()
    if form.validate_on_submit():
        api.http("POST", f"splits/{id}/participants", data=form.data)
        return redirect(url_for("split.detail", id=split.id))
    return render_template("split/add_participant.jinja2", form=form, split=split)


@split_bp.route(
    "/<int:id>/participants/<int:entity_id>/remove", methods=["GET", "POST"]
)
@token_required
def remove_participant(id, entity_id):
    api = get_refinance_api_client()
    split = Split(**api.http("GET", f"splits/{id}").json())
    entity = Entity(**api.http("GET", f"entities/{entity_id}").json())
    form = DeleteForm()
    if form.validate_on_submit():
        api.http("DELETE", f"splits/{id}/participants", params={"entity_id": entity.id})
        return redirect(url_for("split.detail", id=split.id))
    return render_template(
        "split/remove_participant.jinja2", form=form, split=split, entity=entity
    )
