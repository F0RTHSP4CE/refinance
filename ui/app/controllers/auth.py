from flask import Blueprint, redirect, render_template, request, session, url_for

auth_bp = Blueprint("auth", __name__)
from app.external.refinance import get_refinance_api_client
from app.schemas import Balance, Entity, Transaction
from flask import Blueprint, redirect, render_template, url_for
from flask_wtf import FlaskForm
from wtforms import FormField, IntegerField, StringField, SubmitField
from wtforms.validators import DataRequired

entity_bp = Blueprint("entity", __name__)


class TokenRequestForm(FlaskForm):
    entity_name = StringField(
        "Name",
        description="Enter your Telegram username or Entity name",
        render_kw={"placeholder": "username"},
    )
    submit = SubmitField("Login")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    form = TokenRequestForm()
    report = None

    if form.validate_on_submit():
        api = get_refinance_api_client()

        data = {}
        if form.entity_name.data:
            data["entity_name"] = form.entity_name.data

        response = api.http("POST", "tokens/send", data=data)
        report = response.json()

    return render_template("auth/login.jinja2", form=form, report=report)


@auth_bp.route("/token/<token>", methods=["GET"])
def token_auth(token: str):
    if token:
        session["token"] = token
        return redirect(url_for("index.index"))
    return "Invalid Token", 400


@auth_bp.route("/logout", methods=["GET"])
def logout():
    if session.get("token"):
        session.pop("token")
    return redirect(url_for("auth.login"))
