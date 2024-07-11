from app.external.refinance import get_refinance_api_client
from app.middlewares.auth import token_required
from app.schemas import Balance, Entity, Transaction
from flask import Blueprint, redirect, render_template, url_for
from flask_wtf import FlaskForm
from wtforms import BooleanField, StringField, SubmitField
from wtforms.validators import DataRequired

entity_bp = Blueprint("entity", __name__)


class EntityForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired()])
    comment = StringField("Comment")
    telegram_id = StringField("Telegram ID")
    active = BooleanField("Active", default=True)
    submit = SubmitField("Submit")


@entity_bp.route("/")
@token_required
def list():
    api = get_refinance_api_client()
    return render_template(
        "entity/list.jinja2",
        entities=[Entity(**x) for x in api.http("GET", "entities").json()["items"]],
    )


@entity_bp.route("/add", methods=["GET", "POST"])
@token_required
def add():
    form = EntityForm()
    if form.validate_on_submit():
        api = get_refinance_api_client()
        data = form.data
        data.pop("csrf_token")
        api.http("POST", "entities", data=data)
        return redirect(url_for("entity.list"))
    return render_template("entity/add.jinja2", form=form)


@entity_bp.route("/<int:id>")
@token_required
def detail(id):
    api = get_refinance_api_client()
    return render_template(
        "entity/detail.jinja2",
        entity=Entity(**api.http("GET", f"entities/{id}").json()),
        balance=Balance(**api.http("GET", f"balances/{id}").json()),
        transactions=[
            Transaction(**x)
            for x in api.http(
                "GET",
                "transactions",
                params=dict(entity_id=id),
            ).json()["items"]
        ],
    )


@entity_bp.route("/<int:id>/edit", methods=["GET", "POST"])
@token_required
def edit(id):
    api = get_refinance_api_client()
    entity = Entity(**api.http("GET", f"entities/{id}").json())
    form = EntityForm(**entity.__dict__)
    if form.validate_on_submit():
        api.http("PATCH", f"entities/{id}", data=form.data)
        return redirect(url_for("entity.detail", id=id))
    return render_template(
        "entity/edit.jinja2",
        entity=entity,
        form=form,
    )
