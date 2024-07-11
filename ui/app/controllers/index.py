from app.middlewares.auth import token_required
from flask import Blueprint, render_template

index_bp = Blueprint("index", __name__)


@index_bp.route("/")
@token_required
def index():
    return render_template("index.jinja2")
