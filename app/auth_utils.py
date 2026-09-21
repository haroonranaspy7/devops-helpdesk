from functools import wraps

from flask import session, jsonify

from app import db
from app.models.user import User


def get_current_user():
    user_id = session.get("user_id")

    if not user_id:
        return None

    return db.session.get(User, user_id)


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()

        if not user:
            return jsonify({
                "error": "Authentication required"
            }), 401

        return f(*args, **kwargs)

    return decorated_function


def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = get_current_user()

            if not user:
                return jsonify({
                    "error": "Authentication required"
                }), 401

            if user.role not in roles:
                return jsonify({
                    "error": "Insufficient permissions"
                }), 403

            return f(*args, **kwargs)

        return decorated_function

    return decorator
