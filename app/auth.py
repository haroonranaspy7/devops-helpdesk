from flask import Blueprint, request, jsonify, session
from app import db
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
