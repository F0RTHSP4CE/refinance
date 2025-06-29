from app.external.refinance import get_refinance_api_client
from app.middlewares.auth import token_required
from app.schemas import Treasury
from flask import Blueprint, redirect, render_template, request, url_for
from flask_wtf import FlaskForm
from wtforms import BooleanField, StringField, SubmitField
from wtforms.validators import DataRequired

# Treasury blueprint
treasury_bp = Blueprint("treasury", __name__)


# Form for create/edit
class TreasuryForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired()])
    comment = StringField("Comment")
    active = BooleanField("Active", default=True)
    submit = SubmitField("Submit")


# Form for delete confirmation
class DeleteForm(FlaskForm):
    delete = SubmitField("Delete")


@treasury_bp.route("/")
@token_required
def list():
    page = request.args.get("page", 1, type=int)
    limit = request.args.get("limit", 10, type=int)
    skip = (page - 1) * limit
    api = get_refinance_api_client()
    resp = api.http("GET", "treasuries", params={"skip": skip, "limit": limit}).json()
    treasuries = [Treasury(**x) for x in resp["items"]]
    total = resp.get("total", 0)
    return render_template(
        "treasury/list.jinja2",
        treasuries=treasuries,
        total=total,
        page=page,
        limit=limit,
    )


@treasury_bp.route("/add", methods=["GET", "POST"])
@token_required
def add():
    form = TreasuryForm()
    if form.validate_on_submit():
        api = get_refinance_api_client()
        data = form.data.copy()
        data.pop("csrf_token", None)
        api.http("POST", "treasuries", data=data)
        return redirect(url_for("treasury.list"))
    return render_template("treasury/add.jinja2", form=form)


@treasury_bp.route("/<int:id>")
@token_required
def detail(id):
    api = get_refinance_api_client()
    t_data = api.http("GET", f"treasuries/{id}").json()
    treasury = Treasury(**t_data)
    # balances are already part of treasury.balances
    return render_template(
        "treasury/detail.jinja2", treasury=treasury, balance=treasury.balances
    )


@treasury_bp.route("/<int:id>/edit", methods=["GET", "POST"])
@token_required
def edit(id):
    api = get_refinance_api_client()
    t_data = api.http("GET", f"treasuries/{id}").json()
    treasury = Treasury(**t_data)
    form = TreasuryForm(data=t_data)
    if form.validate_on_submit():
        data = form.data.copy()
        data.pop("csrf_token", None)
        api.http("PATCH", f"treasuries/{id}", data=data)
        return redirect(url_for("treasury.detail", id=id))
    return render_template("treasury/edit.jinja2", form=form, treasury=treasury)


@treasury_bp.route("/<int:id>/delete", methods=["GET", "POST"])
@token_required
def delete(id):
    api = get_refinance_api_client()
    form = DeleteForm()
    treasury = Treasury(**api.http("GET", f"treasuries/{id}").json())
    if form.validate_on_submit():
        api.http("DELETE", f"treasuries/{id}")
        return redirect(url_for("treasury.list"))
    return render_template("treasury/delete.jinja2", form=form, treasury=treasury)
