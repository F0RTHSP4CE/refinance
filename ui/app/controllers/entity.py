from datetime import date

from app.config import Config
from app.exceptions.base import ApplicationError
from app.external.refinance import get_refinance_api_client
from app.middlewares.auth import token_required
from app.schemas import (
    Balance,
    Entity,
    Invoice,
    InvoiceStatus,
    StripeAuthorization,
    Tag,
    Transaction,
)
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_wtf import FlaskForm
from wtforms import (
    BooleanField,
    FormField,
    SelectMultipleField,
    StringField,
    SubmitField,
)
from wtforms.validators import DataRequired

entity_bp = Blueprint("entity", __name__)


def _format_api_error(exc: ApplicationError, fallback: str) -> str:
    payload = exc.args[0] if exc.args else None
    if isinstance(payload, dict):
        detail = payload.get("error") or payload.get("detail") or payload.get("message")
        if detail:
            detail_text = str(detail)
            if "CHECKOUT_SESSION_ID" in detail_text:
                return (
                    "Stripe session id placeholder was not resolved. "
                    "Please retry adding the card."
                )
            return detail_text
        return str(payload)
    text = str(exc).strip()
    if "CHECKOUT_SESSION_ID" in text:
        return (
            "Stripe session id placeholder was not resolved. "
            "Please retry adding the card."
        )
    return text or fallback


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


@entity_bp.route("/")
@token_required
def list():
    # Retrieve pagination parameters from the query string
    page = request.args.get("page", 1, type=int)
    limit = request.args.get("limit", 50, type=int)
    skip = (page - 1) * limit

    search_query = request.args.get("q", "", type=str).strip()
    requested_tag_id = request.args.get("tags_ids", type=int)
    show_inactive = request.args.get("inactive", "0", type=str) in {
        "1",
        "true",
        "yes",
        "on",
    }
    # Keep search global across all entities, regardless of selected tag.
    selected_tag_id = None if search_query else requested_tag_id

    current_query = request.args.to_dict(flat=True)
    if search_query:
        current_query.pop("tags_ids", None)

    def _build_tag_tab_url(tag_id: int | None, *, include_inactive: bool = True) -> str:
        params = current_query.copy()
        params.pop("page", None)
        params.pop("skip", None)
        params.pop("q", None)
        if not include_inactive:
            params.pop("inactive", None)
        if tag_id is None:
            params.pop("tags_ids", None)
        else:
            params["tags_ids"] = str(tag_id)
        return url_for("entity.list", **params)

    filters = {}
    if selected_tag_id is not None:
        filters["tags_ids"] = selected_tag_id
    filters["active"] = "false" if show_inactive else "true"

    api = get_refinance_api_client()
    if search_query:
        normalized_search = search_query.lower()
        matched_entities: list[Entity] = []
        scan_limit = 200
        scan_skip = 0

        while True:
            scan_response = api.http(
                "GET",
                "entities",
                params={
                    "skip": scan_skip,
                    "limit": scan_limit,
                    "active": filters["active"],
                },
            ).json()
            scan_items = scan_response.get("items", [])
            if not scan_items:
                break

            page_entities = [Entity(**item) for item in scan_items]
            for entity in page_entities:
                name_text = (entity.name or "").lower()
                comment_text = (entity.comment or "").lower()
                if normalized_search in name_text or normalized_search in comment_text:
                    matched_entities.append(entity)

            scan_skip += len(scan_items)
            if scan_skip >= scan_response.get("total", 0):
                break

        total = len(matched_entities)
        entities = matched_entities[skip : skip + limit]
    else:
        response = api.http(
            "GET", "entities", params={"skip": skip, "limit": limit, **filters}
        ).json()
        entities = [Entity(**x) for x in response["items"]]
        total = response["total"]

    tags_response = api.http("GET", "tags", params={"skip": 0, "limit": 200}).json()
    all_tags = [Tag(**x) for x in tags_response["items"]]

    all_tag_ids = {tag.id for tag in all_tags}

    def _tag_id(tag: Tag | dict) -> int | None:
        if isinstance(tag, dict):
            return tag.get("id")
        return getattr(tag, "id", None)

    used_tag_ids: set[int] = set()
    tag_entity_counts: dict[int, int] = {}

    # Avoid per-tag API calls (N+1): walk entities in pages and collect tag usage stats.
    scan_limit = 200
    scan_skip = 0
    while used_tag_ids != all_tag_ids:
        scan_response = api.http(
            "GET",
            "entities",
            params={
                "skip": scan_skip,
                "limit": scan_limit,
                "active": filters["active"],
            },
        ).json()
        scan_items = scan_response.get("items", [])
        if not scan_items:
            break

        for item in scan_items:
            entity_tag_ids = set()
            for tag in item.get("tags", []):
                tag_id = _tag_id(tag)
                if tag_id is not None:
                    entity_tag_ids.add(tag_id)
                    used_tag_ids.add(tag_id)
            for tag_id in entity_tag_ids:
                tag_entity_counts[tag_id] = tag_entity_counts.get(tag_id, 0) + 1

        scan_skip += len(scan_items)
        if scan_skip >= scan_response.get("total", 0):
            break

    tags_with_entities = sorted(
        (tag for tag in all_tags if tag.id in used_tag_ids),
        key=lambda tag: (-tag_entity_counts.get(tag.id, 0), tag.name.lower()),
    )

    tag_tab_urls = {tag.id: _build_tag_tab_url(tag.id) for tag in tags_with_entities}
    clear_tag_url = _build_tag_tab_url(None, include_inactive=False)

    entity_ids = [entity.id for entity in entities]
    balances_response = api.http(
        "GET",
        "balances",
        params={"entity_ids": entity_ids},
    ).json()

    balances = {}
    currencies = set()
    for entity in entities:
        balance_data = balances_response.get(
            str(entity.id), {"completed": {}, "draft": {}}
        )
        balance = Balance(**balance_data)
        balances[entity.id] = balance
        currencies.update(balance.completed.keys())
        currencies.update(balance.draft.keys())
    currency_columns = sorted(currencies)

    # Sort entities by balance when a tag is selected
    if selected_tag_id is not None:

        def _calculate_total_balance(entity: Entity) -> float:
            balance = balances.get(entity.id)
            if not balance or not balance.completed:
                return 0.0
            # Sum actual values of all completed balances across currencies
            return sum(float(amount) for amount in balance.completed.values())

        entities = sorted(entities, key=_calculate_total_balance, reverse=True)

    return render_template(
        "entity/list.jinja2",
        entities=entities,
        balances=balances,
        currency_columns=currency_columns,
        total=total,
        page=page,
        limit=limit,
        search_query=search_query,
        all_tags=tags_with_entities,
        show_inactive=show_inactive,
        selected_tag_id=selected_tag_id,
        tag_tab_urls=tag_tab_urls,
        clear_tag_url=clear_tag_url,
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


@entity_bp.route("/<int:id>", methods=["GET", "POST"])
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
    if request.method == "POST":
        action = (request.form.get("stripe_action") or "").strip().lower()
        try:
            if action == "add":
                success_base_url = url_for("entity.detail", id=id, _external=True)
                separator = "&" if "?" in success_base_url else "?"
                params = {
                    "entity_id": id,
                    "mode": "entity_dynamic",
                    "success_url": (
                        f"{success_base_url}{separator}"
                        "stripe_session_id={CHECKOUT_SESSION_ID}"
                    ),
                    "cancel_url": url_for("entity.detail", id=id, _external=True),
                }

                response = api.http(
                    "POST",
                    "deposits/providers/stripe/authorizations/setup-session",
                    params=params,
                ).json()
                checkout_url = response.get("checkout_session_url")
                if checkout_url:
                    return redirect(checkout_url)
                flash(
                    "Stripe setup session created, but no checkout URL returned.",
                    "error",
                )
            elif action in {"enable", "disable", "delete", "priority"}:
                auth_id = int(request.form.get("authorization_id", "0") or "0")
                if auth_id <= 0:
                    flash("Invalid authorization id.", "error")
                    return redirect(url_for("entity.detail", id=id))

                if action == "enable":
                    api.http(
                        "POST",
                        f"deposits/providers/stripe/authorizations/{auth_id}/enable",
                    )
                    flash("Card enabled.", "info")
                elif action == "disable":
                    api.http(
                        "POST",
                        f"deposits/providers/stripe/authorizations/{auth_id}/disable",
                    )
                    flash("Card disabled.", "info")
                elif action == "delete":
                    api.http(
                        "DELETE",
                        f"deposits/providers/stripe/authorizations/{auth_id}",
                    )
                    flash("Card deleted.", "info")
                elif action == "priority":
                    priority = int(request.form.get("priority", "1") or "1")
                    api.http(
                        "POST",
                        f"deposits/providers/stripe/authorizations/{auth_id}/priority",
                        params={"priority": max(priority, 1)},
                    )
                    flash("Card priority updated.", "info")
            else:
                flash("Unsupported Stripe action.", "error")
        except ApplicationError as e:
            flash(_format_api_error(e, "Stripe authorization action failed."), "error")
        except Exception as e:
            flash(f"Stripe authorization action failed: {str(e)}", "error")

        return redirect(url_for("entity.detail", id=id))

    stripe_session_id = (request.args.get("stripe_session_id") or "").strip()
    if stripe_session_id and "CHECKOUT_SESSION_ID" not in stripe_session_id:
        try:
            api.http(
                "POST",
                "deposits/providers/stripe/authorizations/sync-session",
                params={
                    "checkout_session_id": stripe_session_id,
                    "entity_id": id,
                },
            ).json()
            flash("Card authorization synchronized.", "success")
        except ApplicationError as e:
            flash(
                _format_api_error(e, "Could not synchronize Stripe setup session."),
                "error",
            )
        except Exception as e:
            flash(f"Could not synchronize Stripe setup session: {str(e)}", "error")
    elif stripe_session_id:
        flash(
            "Stripe session id placeholder was not resolved. Please retry adding the card.",
            "error",
        )

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
            "from_entity_id": id,
        },
    ).json()
    invoices_total = invoices_page["total"]
    invoices = [Invoice(**item) for item in invoices_page["items"]]

    invoices_unpaid_count = (
        api.http(
            "GET",
            "invoices",
            params={"from_entity_id": id, "status": "pending", "skip": 0, "limit": 1},
        )
        .json()
        .get("total", 0)
    )

    if Config.STRIPE_CONFIGURED:
        authorizations_resp = api.http(
            "GET",
            "deposits/providers/stripe/authorizations",
            params={"entity_id": id},
        ).json()
        stripe_authorizations = [
            StripeAuthorization(**item) for item in authorizations_resp.get("items", [])
        ]
    else:
        stripe_authorizations = []

    # For paid invoices, prefer the settled transaction amount/currency in compact UI.
    for invoice in invoices[:6]:
        status = (
            invoice.status.value
            if isinstance(invoice.status, InvoiceStatus)
            else str(invoice.status).lower()
        )
        if status != InvoiceStatus.PAID.value or not invoice.transaction_id:
            continue

        tx_data = api.http("GET", f"transactions/{invoice.transaction_id}").json()
        tx = Transaction(**tx_data)
        invoice.paid_amount = tx.amount
        invoice.paid_currency = tx.currency.upper()

    def _apply_stats_bundle(bundle: dict):
        if not bundle or bundle.get("cached") is False:
            return False, [], [], [], [], [], [], [], [], [], [], []
        return (
            True,
            bundle.get("balance_changes", []),
            bundle.get("transactions_by_day", []),
            bundle.get("money_flow_by_day", []),
            bundle.get("top_incoming", []),
            bundle.get("top_outgoing", []),
            bundle.get("top_incoming_tags", []),
            bundle.get("top_outgoing_tags", []),
            bundle.get("incoming_by_entity_by_month", []),
            bundle.get("outgoing_by_entity_by_month", []),
            bundle.get("incoming_by_tag_by_month", []),
            bundle.get("outgoing_by_tag_by_month", []),
        )

    stats_loaded = False
    balance_changes = []
    transactions_by_day = []
    money_flow_by_day = []
    top_incoming = []
    top_outgoing = []
    top_incoming_tags = []
    top_outgoing_tags = []
    incoming_by_entity_by_month = []
    outgoing_by_entity_by_month = []
    incoming_by_tag_by_month = []
    outgoing_by_tag_by_month = []

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
        money_flow_by_day,
        top_incoming,
        top_outgoing,
        top_incoming_tags,
        top_outgoing_tags,
        incoming_by_entity_by_month,
        outgoing_by_entity_by_month,
        incoming_by_tag_by_month,
        outgoing_by_tag_by_month,
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
            money_flow_by_day,
            top_incoming,
            top_outgoing,
            top_incoming_tags,
            top_outgoing_tags,
            incoming_by_entity_by_month,
            outgoing_by_entity_by_month,
            incoming_by_tag_by_month,
            outgoing_by_tag_by_month,
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
        invoices_unpaid_count=invoices_unpaid_count,
        stripe_authorizations=stripe_authorizations,
        stripe_configured=Config.STRIPE_CONFIGURED,
        invoice_page=invoice_page,
        invoice_limit=invoice_limit,
        balance_changes=balance_changes,
        transactions_by_day=transactions_by_day,
        money_flow_by_day=money_flow_by_day,
        top_incoming=top_incoming,
        top_outgoing=top_outgoing,
        top_incoming_tags=top_incoming_tags,
        top_outgoing_tags=top_outgoing_tags,
        incoming_by_entity_by_month=incoming_by_entity_by_month,
        outgoing_by_entity_by_month=outgoing_by_entity_by_month,
        incoming_by_tag_by_month=incoming_by_tag_by_month,
        outgoing_by_tag_by_month=outgoing_by_tag_by_month,
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
