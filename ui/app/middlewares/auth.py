from flask import session, redirect, url_for, request
from functools import wraps


def token_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "token" not in session:
            return redirect(url_for("auth.login", next=request.url))
        return f(*args, **kwargs)

    return decorated_function
