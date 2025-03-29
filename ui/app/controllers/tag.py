from app.external.refinance import get_refinance_api_client
from app.middlewares.auth import token_required
from app.schemas import Tag
from flask import Blueprint, redirect, render_template, url_for
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
    api = get_refinance_api_client()
    return render_template(
        "tag/list.jinja2",
        tags=[Tag(**x) for x in api.http("GET", "tags").json()["items"]],
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
    tag = api.http("GET", f"tags/{id}").json()
    return render_template("tag/detail.jinja2", tag=Tag(**tag))


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
