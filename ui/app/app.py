import re

from app.controllers.auth import auth_bp
from app.controllers.entity import entity_bp
from app.controllers.exchange import exchange_bp
from app.controllers.index import index_bp
from app.controllers.split import split_bp
from app.controllers.tag import tag_bp
from app.controllers.transaction import transaction_bp
from app.exceptions.base import ApplicationError
from app.external.refinance import get_refinance_api_client
from app.middlewares.auth import token_required
from flask import (
    Flask,
    g,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_cors import CORS

app = Flask(__name__)
app.secret_key = "supersecret"
CORS(app)

app.register_blueprint(index_bp, url_prefix="/")
app.register_blueprint(auth_bp, url_prefix="/auth")
app.register_blueprint(entity_bp, url_prefix="/entities")
app.register_blueprint(transaction_bp, url_prefix="/transactions")
app.register_blueprint(split_bp, url_prefix="/splits")
app.register_blueprint(tag_bp, url_prefix="/tags")
app.register_blueprint(exchange_bp, url_prefix="/exchange")


@app.errorhandler(ApplicationError)
def handle_foo_exception(error):
    return render_template("error.jinja2", error=error), 418


@app.before_request
def load_current_user_and_balance():
    if re.match(r"^/auth|^/static", request.path):
        return
    if "token" in session:
        api = get_refinance_api_client()
        r = api.http("GET", "entities/me")
        if r.status_code == 200:
            g.actor_entity = r.json()
            b = api.http("GET", "balances/%s" % g.actor_entity["id"])
            g.actor_entity_balance = b.json()
            return
        else:
            session.pop("token")
    return redirect(url_for("auth.login"))


@app.route("/hx/search", methods=["GET", "POST"])
@token_required
def hx_search():
    api = get_refinance_api_client()
    entities = api.http(
        "GET", "entities", params=dict(name=request.args.get("name"))
    ).json()["items"]
    return render_template("widgets/hx_entity_selector.jinja2", entities=entities)


@app.route("/hx/entity-name/<int:id>")
@token_required
def hx_entity_name(id):
    api = get_refinance_api_client()
    r = api.http("GET", f"entities/{id}")
    if r.status_code == 200:
        return jsonify(r.json()), 200
    else:
        return jsonify({}), 404


# dev
app.jinja_env.auto_reload = True
app.config["TEMPLATES_AUTO_RELOAD"] = True
