from app.constants import ALLOW_CUSTOM_CURRENCY, CURRENCIES, DEFAULT_CURRENCY
from app.external.refinance import get_refinance_api_client
from app.middlewares.auth import token_required
from app.schemas import Balance, Entity, Split, Tag, Transaction
from flask import Blueprint, redirect, render_template, request, url_for
from flask_wtf import FlaskForm
from wtforms import (
    FloatField,
    FormField,
    IntegerField,
    SelectField,
    SelectMultipleField,
    StringField,
    SubmitField,
)
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
        validators=[
            DataRequired(),
            NumberRange(min=0.01, message="Amount must be greater than 0"),
        ],
        render_kw={"placeholder": "10.00", "class": "small"},
    )
    # Currency field with dropdown
    currency_choices = CURRENCIES.copy()
    if ALLOW_CUSTOM_CURRENCY:
        currency_choices.append(("other", "Other (custom)"))

    currency = SelectField(
        "Currency",
        choices=currency_choices,
        default=DEFAULT_CURRENCY,
        validators=[DataRequired()],
        description="Select a currency from the list",
        render_kw={"class": "small"},
    )

    # Optional field for custom currency (only shown when "other" is selected)
    custom_currency = StringField(
        "Custom Currency",
        description="Enter custom currency code (3 letters preferred)",
        render_kw={"placeholder": "XXX", "class": "small", "style": "display:none;"},
    )
    tag_ids = SelectMultipleField(
        "Tags", coerce=int, choices=[], description="Select tags for this split"
    )
    submit = SubmitField("Submit")


class SplitAddParticipant(FlaskForm):
    entity_name = StringField("Entity")
    entity_id = IntegerField("", validators=[DataRequired(), NumberRange(min=1)])
    fixed_amount = FloatField(
        "Amount",
        render_kw={"placeholder": "10.00", "class": "small"},
        validators=[
            Optional(),
            NumberRange(min=0.01, message="Amount must be greater than 0"),
        ],
        description="Optional. Automatic share will be recalculated with each participant. Fixed amount will be sent as is.",
    )
    submit = SubmitField("Submit")


# New form for adding participant by tag.
class SplitAddParticipantByTag(FlaskForm):
    entity_tag_id = SelectField(
        "Participant Tag", choices=[], validators=[DataRequired()]
    )
    fixed_amount = FloatField(
        "Amount",
        render_kw={"placeholder": "10.00", "class": "small"},
        validators=[
            Optional(),
            NumberRange(min=0.01, message="Amount must be greater than 0"),
        ],
    )
    submit = SubmitField("Submit by Tag")


class DeleteForm(FlaskForm):
    delete = SubmitField("Delete")


class PerformForm(FlaskForm):
    perform = SubmitField("Perform")


class SplitFilterForm(FlaskForm):
    actor_entity_name = StringField("Actor")
    actor_entity_id = IntegerField("", validators=[NumberRange(min=1)])
    recipient_entity_name = StringField("Recipient")
    recipient_entity_id = IntegerField(
        "", validators=[DataRequired(), NumberRange(min=1)]
    )
    amount_min = FloatField(
        "Amount Min",
        render_kw={"placeholder": "10.00", "class": "small"},
        validators=[
            Optional(),
            NumberRange(min=0, message="Amount must be non-negative"),
        ],
    )
    amount_max = FloatField(
        "Amount Max",
        render_kw={"placeholder": "20.00", "class": "small"},
        validators=[
            Optional(),
            NumberRange(min=0, message="Amount must be non-negative"),
        ],
    )
    currency = StringField(
        "Currency",
        render_kw={"placeholder": "GEL", "class": "small"},
    )
    comment = StringField("Comment")
    performed = SelectField(
        "Performed", choices=[("", ""), ("true", "True"), ("false", "False")]
    )
    submit = SubmitField("Search")


@split_bp.route("/")
@token_required
def list():
    # Retrieve pagination parameters from the query string
    page = request.args.get("page", 1, type=int)
    limit = request.args.get("limit", 10, type=int)
    skip = (page - 1) * limit

    filter_form = SplitFilterForm(request.args)
    # leave only non-empty filters
    filters = {
        key: value
        for (key, value) in filter_form.data.items()
        if value not in (None, "")
    }

    api = get_refinance_api_client()
    response = api.http(
        "GET", "splits", params={"skip": skip, "limit": limit, **filters}
    ).json()
    splits = [Split(**x) for x in response["items"]]
    total = response["total"]

    return render_template(
        "split/list.jinja2",
        splits=splits,
        total=total,
        page=page,
        limit=limit,
        filter_form=filter_form,
    )


@split_bp.route("/add", methods=["GET", "POST"])
@token_required
def add():
    api = get_refinance_api_client()
    form = SplitForm()

    # populate tag choices
    all_tags = [Tag(**x) for x in api.http("GET", "tags").json()["items"]]
    form.tag_ids.choices = [(tag.id, tag.name) for tag in all_tags]

    if form.validate_on_submit():
        data = form.data.copy()
        data.pop("csrf_token", None)

        # Handle custom currency option
        if data.get("currency") == "other" and data.get("custom_currency"):
            data["currency"] = data["custom_currency"].lower()
        data.pop("custom_currency", None)  # Remove custom_currency field from data

        api.http("POST", "splits", data=data)
        return redirect(url_for("split.list"))
    return render_template("split/add.jinja2", form=form, all_tags=all_tags)


@split_bp.route("/<int:id>/edit", methods=["GET", "POST"])
@token_required
def edit(id):
    api = get_refinance_api_client()
    split_data = api.http("GET", f"splits/{id}").json()

    # Check if the existing currency is in our predefined list
    existing_currency = split_data.get("currency", "").upper()
    currency_in_list = any(code == existing_currency for code, _ in CURRENCIES)

    # Prepare form data with tag_ids
    form_data = split_data.copy()
    form_data["tag_ids"] = [tag["id"] for tag in split_data.get("tags", [])]

    # Handle custom currency for backward compatibility
    if not currency_in_list and ALLOW_CUSTOM_CURRENCY and existing_currency:
        form_data["currency"] = "other"
        form_data["custom_currency"] = existing_currency
    elif existing_currency:
        form_data["currency"] = existing_currency

    form = SplitForm(data=form_data)

    # populate tag choices
    all_tags = [Tag(**x) for x in api.http("GET", "tags").json()["items"]]
    form.tag_ids.choices = [(tag.id, tag.name) for tag in all_tags]

    if form.validate_on_submit():
        data = form.data.copy()
        data.pop("csrf_token", None)

        # Handle custom currency option
        if data.get("currency") == "other" and data.get("custom_currency"):
            data["currency"] = data["custom_currency"].lower()
        data.pop("custom_currency", None)  # Remove custom_currency field from data

        api.http("PATCH", f"splits/{id}", data=data)
        return redirect(url_for("split.detail", id=id))

    return render_template(
        "split/edit.jinja2",
        split=split_data,
        form=form,
        all_tags=all_tags,
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
    form_entity = SplitAddParticipant()
    form_tag = SplitAddParticipantByTag()
    tags_response = api.http("GET", "tags").json()
    all_tags = [Tag(**x) for x in tags_response["items"]]
    choices = [("", "-")] + [(str(tag.id), tag.name) for tag in all_tags]
    # Assign choices to the new form's tag field.
    form_tag.entity_tag_id.choices = choices
    if request.method == "POST":
        if form_entity.submit.data and form_entity.validate_on_submit():
            api.http("POST", f"splits/{id}/participants", data=form_entity.data)
            return redirect(url_for("split.detail", id=split.id))
        elif form_tag.submit.data and form_tag.validate_on_submit():
            api.http("POST", f"splits/{id}/participants", data=form_tag.data)
            return redirect(url_for("split.detail", id=split.id))
    return render_template(
        "split/add_participant.jinja2",
        split=split,
        form_entity=form_entity,
        form_tag=form_tag,
        all_tags=all_tags,
    )


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
