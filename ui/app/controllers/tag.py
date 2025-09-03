from app.external.refinance import get_refinance_api_client
from app.middlewares.auth import token_required
from app.schemas import Tag
from flask import Blueprint, redirect, render_template, request, url_for
from flask_wtf import FlaskForm
from wtforms import FormField, StringField, SubmitField
from wtforms.validators import DataRequired

tag_bp = Blueprint("tag", __name__)


class TagForm(FlaskForm):
    name = StringField(
        "Name",
        validators=[DataRequired()],
    )
    comment = StringField("Comment")
    submit = SubmitField("Submit")


class DeleteForm(FlaskForm):
    delete = SubmitField("Delete")


@tag_bp.route("/")
@token_required
def list():
    # Get current page and limit from query parameters (defaults: page 1, 10 items per page)
    page = request.args.get("page", 1, type=int)
    limit = request.args.get("limit", 20, type=int)
    skip = (page - 1) * limit

    api = get_refinance_api_client()
    # Include skip and limit in your API call for tags
    response = api.http("GET", "tags", params={"skip": skip, "limit": limit}).json()
    tags = [Tag(**x) for x in response["items"]]
    total = response["total"]

    return render_template(
        "tag/list.jinja2",
        tags=tags,
        total=total,
        page=page,
        limit=limit,
    )


@tag_bp.route("/add", methods=["GET", "POST"])
@token_required
def add():
    form = TagForm()
    if form.validate_on_submit():
        api = get_refinance_api_client()
        api.http("POST", "tags", data=form.data)
        return redirect(url_for("tag.list"))

    return render_template("tag/add.jinja2", form=form)


@tag_bp.route("/<int:id>/edit", methods=["GET", "POST"])
@token_required
def edit(id):
    api = get_refinance_api_client()
    tag = api.http("GET", f"tags/{id}").json()
    form = TagForm(data=tag)
    if form.validate_on_submit():
        api.http("PATCH", f"tags/{id}", data=form.data)
        return redirect(url_for("tag.detail", id=id))

    return render_template(
        "tag/edit.jinja2",
        tag=tag,
        form=form,
    )


@tag_bp.route("/<int:id>")
@token_required
def detail(id):
    api = get_refinance_api_client()
    # Fetch tag data and monthly transaction sums by tag
    tag_data = api.http("GET", f"tags/{id}").json()
    tag = Tag(**tag_data)
    tag_stats = api.http(
        "GET", "stats/transactions-sum-by-tag-by-month", params={"tag_id": id}
    ).json()
    # Render template with stats data
    return render_template(
        "tag/detail.jinja2",
        tag=tag,
        tag_stats=tag_stats,
    )


@tag_bp.route("/<int:id>/delete", methods=["GET", "POST"])
@token_required
def delete(id):
    api = get_refinance_api_client()
    tag = Tag(**api.http("GET", f"tags/{id}").json())
    form = DeleteForm()
    if form.validate_on_submit():
        api.http("DELETE", f"tags/{id}")
        return redirect(url_for("tag.list"))
    return render_template("tag/delete.jinja2", form=form, tag=tag)
