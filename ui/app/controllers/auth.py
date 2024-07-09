from flask import Blueprint, redirect, render_template, request, session, url_for

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        token = request.form.get("token")
        if token:
            session["token"] = token
            return redirect(url_for("index.index"))
    return render_template("auth/login.jinja2")


@auth_bp.route("/token", methods=["GET"])
def token_auth():
    token = request.args.get("token")
    if token:
        session["token"] = token
        return redirect(url_for("index.index"))
    return "Invalid Token", 400


@auth_bp.route("/logout", methods=["GET"])
def logout():
    session.pop("token")
    return redirect(url_for("auth.login"))
