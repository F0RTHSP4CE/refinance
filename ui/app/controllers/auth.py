import re

import requests
from app.config import config
from app.external.refinance import get_refinance_api_client
from flask import (
    Blueprint,
    Response,
    current_app,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField

auth_bp = Blueprint("auth", __name__)


class TokenRequestForm(FlaskForm):
    entity_name = StringField("Name")
    submit = SubmitField("Request")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    form = TokenRequestForm()
    if form.validate_on_submit():
        api = get_refinance_api_client()
        report = api.http("POST", "tokens/request", data=form.data)
        return render_template("auth/report.jinja2", report=report.json())
    return render_template("auth/login.jinja2", form=form)


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


def _strip_domain_path(cookie: str) -> str:
    # Remove Domain and Path attributes for compatibility with UI domain
    cookie = re.sub(r";\s*Domain=[^;]+", "", cookie, flags=re.IGNORECASE)
    cookie = re.sub(r";\s*Path=[^;]+", "", cookie, flags=re.IGNORECASE)
    return cookie


def _proxy_oidc_backend(backend_url, params):
    resp = requests.get(
        backend_url,
        params=params,
        allow_redirects=False,
        cookies=request.cookies,
        stream=True,
        headers={"Host": request.host},
        verify=False,  # Disable SSL verification for local development
    )
    set_cookie_headers = (
        resp.raw.headers.get_all("Set-Cookie")
        if hasattr(resp.raw.headers, "get_all")
        else (
            resp.headers.getlist("Set-Cookie")
            if hasattr(resp.headers, "getlist")
            else []
        )
    )
    headers = [
        (k, v)
        for k, v in resp.headers.items()
        if k.lower() not in ("content-encoding", "set-cookie")
    ]
    for cookie in set_cookie_headers:
        headers.append(("Set-Cookie", _strip_domain_path(cookie)))
    return resp, headers


@auth_bp.route("/oidc/login", methods=["GET"])
def oidc_login():
    backend_url = f"{config.REFINANCE_API_BASE_URL}/auth/oidc/login"
    resp, headers = _proxy_oidc_backend(backend_url, request.args)
    return Response(resp.content, status=resp.status_code, headers=headers)


@auth_bp.route("/oidc/callback", methods=["GET"])
def oidc_callback():
    backend_url = f"{config.REFINANCE_API_BASE_URL}/auth/oidc/callback"
    resp, headers = _proxy_oidc_backend(backend_url, request.args)
    if resp.is_redirect and resp.headers.get("Location", "").startswith("/auth/token/"):
        token = resp.headers["Location"].split("/auth/token/")[-1]
        return token_auth(token)
    return Response(resp.content, status=resp.status_code, headers=headers)
