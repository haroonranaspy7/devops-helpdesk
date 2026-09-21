from flask import Blueprint, jsonify, request, session

from app import db
from app.auth_utils import get_current_user, login_required
from app.models.user import User
auth = Blueprint("auth", __name__, url_prefix="/auth")


@auth.route("/register", methods=["POST"])
def register():
    data = request.get_json() or {}

    username = data.get("username", "").strip()
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not username or not email or not password:
        return jsonify({
            "error": "Username, email and password are required"
        }), 400

    if len(password) < 8:
        return jsonify({
            "error": "Password must be at least 8 characters"
        }), 400

    if User.query.filter_by(username=username).first():
        return jsonify({
            "error": "Username already exists"
        }), 409

    if User.query.filter_by(email=email).first():
        return jsonify({
            "error": "Email already exists"
        }), 409

    user = User(
        username=username,
        email=email,
        role="USER"
    )

    user.set_password(password)

    db.session.add(user)
    db.session.commit()

    return jsonify({
        "message": "User registered successfully",
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role
        }
    }), 201


@auth.route("/login", methods=["POST"])
def login():
    data = request.get_json() or {}

    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not email or not password:
        return jsonify({
            "error": "Email and password are required"
        }), 400

    user = User.query.filter_by(email=email).first()

    if not user or not user.check_password(password):
        return jsonify({
            "error": "Invalid email or password"
        }), 401

    session["user_id"] = user.id

    return jsonify({
        "message": "Login successful",
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role
        }
    }), 200


@auth.route("/logout", methods=["POST"])
def logout():
    session.pop("user_id", None)

    return jsonify({
        "message": "Logout successful"
    }), 200

@auth.route("/change-password", methods=["POST"])
@login_required
def change_password():
    data = request.get_json() or {}

    current_password = data.get("current_password", "")
    new_password = data.get("new_password", "")
    confirm_password = data.get("confirm_password", "")

    if not all(
        isinstance(value, str)
        for value in (
            current_password,
            new_password,
            confirm_password,
        )
    ):
        return jsonify({
            "error": "Password values must be text"
        }), 400

    if (
        not current_password
        or not new_password
        or not confirm_password
    ):
        return jsonify({
            "error": (
                "Current password, new password, "
                "and confirmation are required"
            )
        }), 400

    if len(new_password) < 8:
        return jsonify({
            "error": "New password must be at least 8 characters"
        }), 400

    if new_password != confirm_password:
        return jsonify({
            "error": "New password and confirmation do not match"
        }), 400

    user = get_current_user()

    if not user.check_password(current_password):
        return jsonify({
            "error": "Current password is incorrect"
        }), 400

    if user.check_password(new_password):
        return jsonify({
            "error": (
                "New password must be different "
                "from the current password"
            )
        }), 400

    user.set_password(new_password)
    db.session.commit()

    return jsonify({
        "message": "Password changed successfully"
    }), 200

@auth.route("/me", methods=["GET"])
def me():
    user_id = session.get("user_id")

    if not user_id:
        return jsonify({
            "error": "Not authenticated"
        }), 401

    user = db.session.get(User, user_id)

    if not user:
        session.pop("user_id", None)

        return jsonify({
            "error": "User not found"
        }), 401

    return jsonify({
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role
        }
    }), 200
