from app.external.refinance import get_refinance_api_client
from app.middlewares.auth import token_required
from app.schemas import Balance, Entity, Tag, Transaction
from flask import Blueprint, redirect, render_template, request, url_for
from flask_wtf import FlaskForm
from wtforms import (
    FormField,
    SelectField,
    SelectMultipleField,
    StringField,
    SubmitField,
)
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
    tag_ids = SelectMultipleField(
        "Tags", coerce=int, choices=[], description="Select tags for this entity"
    )


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


class AddCardForm(FlaskForm):
    comment = StringField(
        "Comment",
        description="Optional card label",
        render_kw={"placeholder": "main card"},
    )
    card_hash = StringField(
        "Card Hash",
        validators=[DataRequired()],
        description="Unique card hash",
        render_kw={"placeholder": "a1bc23d45e678f90g123h456i789j0kl"},
    )
    submit = SubmitField("Add Card")


class DeleteForm(FlaskForm):
    delete = SubmitField("Delete")


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
    limit = request.args.get("limit", 20, type=int)
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
    api = get_refinance_api_client()
    entity_form = EntityForm(prefix="entity")
    auth_form = AuthForm(prefix="auth")

    # Populate tag choices
    all_tags = [Tag(**x) for x in api.http("GET", "tags").json()["items"]]
    entity_form.tag_ids.choices = [(tag.id, tag.name) for tag in all_tags]

    if entity_form.validate_on_submit() and auth_form.validate_on_submit():
        # Combine data from both forms into a single dictionary.
        data = {
            "name": entity_form.name.data,
            "comment": entity_form.comment.data,
            "tag_ids": entity_form.tag_ids.data,
            "auth": auth_form.data,  # This includes telegram_id, signal_id, whatsapp_number, email
        }
        # Remove CSRF tokens from both dictionaries if present.
        data.pop("csrf_token", None)
        data["auth"].pop("csrf_token", None)

        api.http("POST", "entities", data=data)
        return redirect(url_for("entity.list"))

    return render_template(
        "entity/add.jinja2",
        entity_form=entity_form,
        auth_form=auth_form,
        all_tags=all_tags,
    )


@entity_bp.route("/<int:id>/edit", methods=["GET", "POST"])
@token_required
def edit(id):
    api = get_refinance_api_client()
    # Get the entity data from the API; entity.auth is a dict of auth fields.
    entity_data = api.http("GET", f"entities/{id}").json()
    entity = Entity(**entity_data)

    # Prepare form data with tag_ids
    form_data = entity_data.copy()
    form_data["tag_ids"] = [tag["id"] for tag in entity_data.get("tags", [])]

    # Create separate form instances with prefixes. Pre-populate:
    entity_form = EntityForm(prefix="entity", data=form_data)
    # If the entity_data does not include auth keys at the root level,
    # extract them (or default to an empty dict).
    auth_data = entity_data.get("auth", {})
    auth_form = AuthForm(prefix="auth", data=auth_data)

    # Fetch cards for this entity
    cards_data = api.http("GET", f"entities/{id}/cards").json()

    # Populate tag choices
    all_tags = [Tag(**x) for x in api.http("GET", "tags").json()["items"]]
    entity_form.tag_ids.choices = [(tag.id, tag.name) for tag in all_tags]

    # On POST, validate both forms.
    if entity_form.validate_on_submit() and auth_form.validate_on_submit():
        # Combine the data from both forms.
        combined_data = {
            "name": entity_form.name.data,
            "comment": entity_form.comment.data,
            "tag_ids": entity_form.tag_ids.data,
            "auth": auth_form.data,  # This is the dict containing telegram_id, signal_id, etc.
        }
        api.http("PATCH", f"entities/{id}", data=combined_data)
        return redirect(url_for("entity.detail", id=id))

    return render_template(
        "entity/edit.jinja2",
        entity=entity,
        entity_form=entity_form,
        auth_form=auth_form,
        all_tags=all_tags,
        cards=cards_data,
        add_card_form=AddCardForm(prefix="card"),
    )


@entity_bp.route("/<int:id>")
@token_required
def detail(id):
    page = request.args.get("page", 1, type=int)
    limit = request.args.get("limit", 20, type=int)
    skip = (page - 1) * limit

    api = get_refinance_api_client()
    entity_data = api.http("GET", f"entities/{id}").json()
    cards_data = api.http("GET", f"entities/{id}/cards").json()
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
        cards=cards_data,
    )


@entity_bp.route("/<int:id>/cards", methods=["POST"])
@token_required
def add_card(id):
    api = get_refinance_api_client()
    form = AddCardForm(prefix="card")
    if form.validate_on_submit():
        payload = {
            "comment": form.comment.data or None,
            "card_hash": form.card_hash.data,
        }
        api.http("POST", f"entities/{id}/cards", data=payload)
    return redirect(url_for("entity.edit", id=id))


@entity_bp.route("/<int:id>/cards/<int:card_id>/delete", methods=["GET", "POST"])
@token_required
def delete_card(id, card_id):
    api = get_refinance_api_client()
    form = DeleteForm()
    if form.validate_on_submit():
        api.http("DELETE", f"entities/{id}/cards/{card_id}")
        return redirect(url_for("entity.edit", id=id))
    # Fetch card info for confirmation page
    cards = api.http("GET", f"entities/{id}/cards").json()
    card = next((c for c in cards if c.get("id") == card_id), None)
    return render_template(
        "entity/card_delete.jinja2", form=form, card=card, entity_id=id
    )
