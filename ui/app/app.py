import re

from app.controllers.auth import auth_bp
from app.controllers.entity import entity_bp
from app.controllers.index import index_bp
from app.controllers.transaction import transaction_bp
from app.exceptions.base import ApplicationError
from app.external.refinance import get_refinance_api_client
from flask import Flask, g, redirect, render_template, request, session, url_for
from flask_cors import CORS

app = Flask(__name__)
app.secret_key = "supersecret"
CORS(app)

app.register_blueprint(index_bp, url_prefix="/")
app.register_blueprint(auth_bp, url_prefix="/auth")
app.register_blueprint(entity_bp, url_prefix="/entities")
app.register_blueprint(transaction_bp, url_prefix="/transactions")


@app.errorhandler(ApplicationError)
def handle_foo_exception(error):
    return render_template("error.jinja2", error=error), 418


@app.before_request
def load_current_user():
    if re.match(r"^/auth|^/static", request.path):
        return
    if "token" in session:
        api = get_refinance_api_client()
        r = api.http("GET", "entities/me")
        if r.status_code == 200:
            g.actor_entity = r.json()
            return
        else:
            session.pop("token")
    return redirect(url_for("auth.login"))


# dev
app.jinja_env.auto_reload = True
app.config["TEMPLATES_AUTO_RELOAD"] = True
