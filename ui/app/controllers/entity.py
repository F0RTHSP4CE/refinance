from datetime import date

from app.external.refinance import get_refinance_api_client
from app.middlewares.auth import token_required
from app.schemas import Balance, Entity, Invoice, Tag, Transaction
from flask import Blueprint, redirect, render_template, request, url_for
from flask_wtf import FlaskForm
from wtforms import (
    BooleanField,
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
    active = BooleanField("Active", default=True)
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


class EntityFilterForm(FlaskForm):
    name = StringField("Name")
    comment = StringField("Comment")
    active = SelectField(
        "Active", choices=[("", ""), ("true", "Active"), ("false", "Inactive")]
    )
    balance_currency = StringField("Balance Currency")
    balance_status = SelectField(
        "Balance Status",
        choices=[("", ""), ("completed", "Completed"), ("draft", "Draft")],
    )
    balance_order = SelectField(
        "Balance Order",
        choices=[("", ""), ("desc", "Highest first"), ("asc", "Lowest first")],
    )
    submit = SubmitField("Search")


@entity_bp.route("/")
@token_required
def list():
    # Retrieve pagination parameters from the query string
    page = request.args.get("page", 1, type=int)
    limit = request.args.get("limit", 50, type=int)
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

    balances = {}
    currencies = set()
    for entity in entities:
        balance_data = api.http("GET", f"balances/{entity.id}").json()
        balance = Balance(**balance_data)
        balances[entity.id] = balance
        currencies.update(balance.completed.keys())
        currencies.update(balance.draft.keys())
    currency_columns = sorted(currencies)

    return render_template(
        "entity/list.jinja2",
        entities=entities,
        balances=balances,
        currency_columns=currency_columns,
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
            "active": entity_form.active.data,
        }
        api.http("PATCH", f"entities/{id}", data=combined_data)
        return redirect(url_for("entity.detail", id=id))

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

    invoice_page = request.args.get("invoice_page", 1, type=int)
    invoice_limit = request.args.get("invoice_limit", 20, type=int)
    invoice_skip = (invoice_page - 1) * invoice_limit

    stats_requested = request.args.get("stats", "", type=str).lower() in (
        "1",
        "true",
        "yes",
        "on",
    )

    stats_months = request.args.get("stats_months", 6, type=int)
    stats_limit = request.args.get("stats_limit", 6, type=int)
    stats_months = max(1, stats_months)
    stats_limit = max(1, stats_limit)

    api = get_refinance_api_client()
    entity_data = api.http("GET", f"entities/{id}").json()
    balance_data = api.http("GET", f"balances/{id}").json()
    transactions_page = api.http(
        "GET", "transactions", params={"skip": skip, "limit": limit, "entity_id": id}
    ).json()
    total = transactions_page["total"]

    invoices_page = api.http(
        "GET",
        "invoices",
        params={
            "skip": invoice_skip,
            "limit": invoice_limit,
            "entity_id": id,
        },
    ).json()
    invoices_total = invoices_page["total"]
    invoices = [Invoice(**item) for item in invoices_page["items"]]

    def _apply_stats_bundle(bundle: dict):
        if not bundle or bundle.get("cached") is False:
            return False, [], [], [], [], [], []
        return (
            True,
            bundle.get("balance_changes", []),
            bundle.get("transactions_by_day", []),
            bundle.get("top_incoming", []),
            bundle.get("top_outgoing", []),
            bundle.get("top_incoming_tags", []),
            bundle.get("top_outgoing_tags", []),
        )

    stats_loaded = False
    balance_changes = []
    transactions_by_day = []
    top_incoming = []
    top_outgoing = []
    top_incoming_tags = []
    top_outgoing_tags = []

    # Always try to preload from cache (fast on hit, no DB work on miss).
    cached_bundle = api.http(
        "GET",
        f"stats/entity/{id}",
        params={
            "limit": stats_limit,
            "months": stats_months,
            "timeframe_to": date.today().isoformat(),
            "cached_only": 1,
        },
    ).json()

    (
        stats_loaded,
        balance_changes,
        transactions_by_day,
        top_incoming,
        top_outgoing,
        top_incoming_tags,
        top_outgoing_tags,
    ) = _apply_stats_bundle(cached_bundle)

    if not stats_loaded and stats_requested:
        # User explicitly requested calculation/loading.
        stats_bundle = api.http(
            "GET",
            f"stats/entity/{id}",
            params={
                "limit": stats_limit,
                "months": stats_months,
                "timeframe_to": date.today().isoformat(),
            },
        ).json()

        (
            stats_loaded,
            balance_changes,
            transactions_by_day,
            top_incoming,
            top_outgoing,
            top_incoming_tags,
            top_outgoing_tags,
        ) = _apply_stats_bundle(stats_bundle)

    return render_template(
        "entity/detail.jinja2",
        entity=Entity(**entity_data),
        balance=Balance(**balance_data),
        transactions=[Transaction(**x) for x in transactions_page["items"]],
        total=total,
        page=page,
        limit=limit,
        invoices=invoices,
        invoices_total=invoices_total,
        invoice_page=invoice_page,
        invoice_limit=invoice_limit,
        balance_changes=balance_changes,
        transactions_by_day=transactions_by_day,
        top_incoming=top_incoming,
        top_outgoing=top_outgoing,
        top_incoming_tags=top_incoming_tags,
        top_outgoing_tags=top_outgoing_tags,
        stats_loaded=stats_loaded,
        stats_months=stats_months,
        stats_limit=stats_limit,
    )


@entity_bp.route("/<int:id>/stats")
@token_required
def stats(id):
    """Trigger calculation / loading of cached statistics for an entity."""

    page = request.args.get("page", 1, type=int)
    limit = request.args.get("limit", 20, type=int)
    stats_months = request.args.get("stats_months", 6, type=int)
    stats_limit = request.args.get("stats_limit", 6, type=int)
    stats_months = max(1, stats_months)
    stats_limit = max(1, stats_limit)

    return redirect(
        url_for(
            "entity.detail",
            id=id,
            page=page,
            limit=limit,
            stats=1,
            stats_months=stats_months,
            stats_limit=stats_limit,
        )
    )
