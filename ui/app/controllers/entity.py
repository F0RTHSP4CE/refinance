from app.external.refinance import get_refinance_api_client
from app.middlewares.auth import token_required
from app.schemas import Balance, Entity, Transaction
from flask import Blueprint, redirect, render_template, url_for
from flask_wtf import FlaskForm
from wtforms import FormField, StringField, SubmitField
from wtforms.validators import DataRequired

entity_bp = Blueprint("entity", __name__)


class EntityForm(FlaskForm):
    name = StringField(
        "Name",
        validators=[DataRequired()],
        description="Unique, short identifier",
        render_kw={"placeholder": "h4ck3r"},
    )
    comment = StringField("Comment")


class AuthForm(FlaskForm):
    telegram_id = StringField(
        "Telegram ID",
        description="View ID: <a href='https://t.me/myidbot'>t.me/myidbot</a>",
        render_kw={"placeholder": "91827364"},
    )
    signal_id = StringField(
        "Signal ID",
        description="Your Signal identifier",
        render_kw={"placeholder": "+12398732132"},
    )

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
    entity_form = EntityForm(prefix="entity")
    auth_form = AuthForm(prefix="auth")

    if entity_form.validate_on_submit() and auth_form.validate_on_submit():
        # Combine data from both forms into a single dictionary.
        data = {
            "name": entity_form.name.data,
            "comment": entity_form.comment.data,
            "auth": auth_form.data,  # This includes telegram_id, signal_id, whatsapp_number, email
        }
        # Remove CSRF tokens from both dictionaries if present.
        data.pop("csrf_token", None)
        data["auth"].pop("csrf_token", None)

        api = get_refinance_api_client()
        api.http("POST", "entities", data=data)
        return redirect(url_for("entity.list"))

    return render_template(
        "entity/add.jinja2", entity_form=entity_form, auth_form=auth_form
    )


@entity_bp.route("/<int:id>/edit", methods=["GET", "POST"])
@token_required
def edit(id):
    api = get_refinance_api_client()
    # Get the entity data from the API; entity.auth is a dict of auth fields.
    entity_data = api.http("GET", f"entities/{id}").json()
    entity = Entity(**entity_data)

    # Create separate form instances with prefixes. Pre-populate:
    entity_form = EntityForm(prefix="entity", data=entity_data)
    # If the entity_data does not include auth keys at the root level,
    # extract them (or default to an empty dict).
    auth_data = entity_data.get("auth", {})
    auth_form = AuthForm(prefix="auth", data=auth_data)

    # On POST, validate both forms.
    if entity_form.validate_on_submit() and auth_form.validate_on_submit():
        # Combine the data from both forms.
        combined_data = {
            "name": entity_form.name.data,
            "comment": entity_form.comment.data,
            "auth": auth_form.data,  # This is the dict containing telegram_id, signal_id, etc.
        }
        api.http("PATCH", f"entities/{id}", data=combined_data)
        return redirect(url_for("entity.detail", id=id))

    return render_template(
        "entity/edit.jinja2",
        entity=entity,
        entity_form=entity_form,
        auth_form=auth_form,
    )


@entity_bp.route("/<int:id>")
@token_required
def detail(id):
    api = get_refinance_api_client()
    entity_data = api.http("GET", f"entities/{id}").json()
    balance_data = api.http("GET", f"balances/{id}").json()
    transactions_data = api.http(
        "GET", "transactions", params=dict(entity_id=id)
    ).json()["items"]

    return render_template(
        "entity/detail.jinja2",
        entity=Entity(**entity_data),
        balance=Balance(**balance_data),
        transactions=[Transaction(**x) for x in transactions_data],
    )
