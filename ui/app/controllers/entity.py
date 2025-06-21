from app.external.refinance import get_refinance_api_client
from app.middlewares.auth import token_required
from app.schemas import Balance, Entity, Tag, Transaction
from flask import Blueprint, redirect, render_template, request, url_for
from flask_wtf import FlaskForm
from wtforms import FormField, SelectField, StringField, SubmitField
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


class EntityFilterForm(FlaskForm):
    name = StringField("Name")
    comment = StringField("Comment")
    active = SelectField(
        "Active", choices=[("", ""), ("true", "Active"), ("false", "Inactive")]
    )
    submit = SubmitField("Search")


@entity_bp.route("/")
@token_required
def list():
    # Retrieve pagination parameters from the query string
    page = request.args.get("page", 1, type=int)
    limit = request.args.get("limit", 10, type=int)
    skip = (page - 1) * limit

    filter_form = EntityFilterForm(request.args)
    # leave only non-empty filters
    filters = {
        key: value
        for (key, value) in filter_form.data.items()
        if value not in (None, "")
    }

    api = get_refinance_api_client()
    response = api.http(
        "GET", "entities", params={"skip": skip, "limit": limit, **filters}
    ).json()
    entities = [Entity(**x) for x in response["items"]]
    total = response["total"]

    return render_template(
        "entity/list.jinja2",
        entities=entities,
        total=total,
        page=page,
        limit=limit,
        filter_form=filter_form,
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

    all_tags = [Tag(**x) for x in api.http("GET", "tags").json()["items"]]
    return render_template(
        "entity/edit.jinja2",
        entity=entity,
        entity_form=entity_form,
        auth_form=auth_form,
        all_tags=all_tags,
    )


@entity_bp.route("/<int:id>")
@token_required
def detail(id):
    page = request.args.get("page", 1, type=int)
    limit = request.args.get("limit", 20, type=int)
    skip = (page - 1) * limit

    api = get_refinance_api_client()
    entity_data = api.http("GET", f"entities/{id}").json()
    balance_data = api.http("GET", f"balances/{id}").json()
    transactions_page = api.http(
        "GET", "transactions", params={"skip": skip, "limit": limit, "entity_id": id}
    ).json()
    total = transactions_page["total"]
    # Fetch stats for this entity
    balance_changes = api.http("GET", f"stats/entity/{id}/balance-change-by-day").json()
    transactions_by_day = api.http(
        "GET", f"stats/entity/{id}/transactions-by-day"
    ).json()

    return render_template(
        "entity/detail.jinja2",
        entity=Entity(**entity_data),
        balance=Balance(**balance_data),
        transactions=[Transaction(**x) for x in transactions_page["items"]],
        total=total,
        page=page,
        limit=limit,
        balance_changes=balance_changes,
        transactions_by_day=transactions_by_day,
    )


@entity_bp.route("/<int:entity_id>/tags/add", methods=["POST"])
@token_required
def add_tag(entity_id):
    tag_id = request.form.get("tag_id", type=int)
    api = get_refinance_api_client()
    api.http("POST", f"entities/{entity_id}/tags", params={"tag_id": tag_id}).json()
    return redirect(url_for("entity.edit", id=entity_id))


@entity_bp.route("/<int:entity_id>/tags/remove", methods=["POST"])
@token_required
def remove_tag(entity_id):
    tag_id = request.form.get("tag_id", type=int)
    api = get_refinance_api_client()
    api.http("DELETE", f"entities/{entity_id}/tags", params={"tag_id": tag_id}).json()
    return redirect(url_for("entity.edit", id=entity_id))
