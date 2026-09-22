import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy.exc import IntegrityError

from app.auth_utils import role_required
from app.models.invitation import Invitation
from flask import (
    Blueprint,
    current_app,
    jsonify,
    request,
    session
)
from app import db
from app.auth_utils import get_current_user, login_required
from app.models.user import User
auth = Blueprint("auth", __name__, url_prefix="/auth")


@auth.route("/register", methods=["POST"])
def register():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({"error": "A JSON object is required"}), 400

    fields = ("username", "email", "password", "invitation_code")

    if not all(isinstance(data.get(field), str) for field in fields):
        return jsonify({
            "error": "Username, email, password and invitation code are required"
        }), 400

    username = data["username"].strip()
    email = data["email"].strip().lower()
    password = data["password"]
    code = data["invitation_code"].strip()

    if not username or not email or not password or not code:
        return jsonify({"error": "All registration fields are required"}), 400

    if len(username) > 100 or len(email) > 255:
        return jsonify({"error": "Username or email is too long"}), 400

    if (
        email.count("@") != 1
        or not all(email.split("@"))
        or any(character.isspace() for character in email)
    ):
        return jsonify({"error": "Enter a valid email address"}), 400

    if not 8 <= len(password) <= 128:
        return jsonify({
            "error": "Password must be between 8 and 128 characters"
        }), 400

    if len(code) > 128:
        return jsonify({"error": "Invalid or unavailable invitation"}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({"error": "Username already exists"}), 409

    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email already exists"}), 409

    user = User(username=username, email=email)
    user.set_password(password)

    code_hash = hashlib.sha256(code.encode("utf-8")).hexdigest()

    try:
        invitation = (
            Invitation.query
            .filter_by(code_hash=code_hash)
            .populate_existing()
            .with_for_update()
            .first()
        )

        now = datetime.now(timezone.utc)

        if (
            invitation is None
            or invitation.used_at is not None
            or invitation.revoked_at is not None
            or invitation.expires_at <= now
            or (
                invitation.email is not None
                and invitation.email != email
            )
        ):
            db.session.rollback()
            return jsonify({
                "error": "Invalid or unavailable invitation"
            }), 400

        # The role comes from the database, never from the signup form.
        user.role = invitation.role

        db.session.add(user)
        invitation.used_at = now

        # Account creation and invitation consumption succeed together.
        db.session.commit()

    except IntegrityError:
        db.session.rollback()
        return jsonify({
            "error": "Username or email already exists"
        }), 409

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
@auth.post("/invitations")
@role_required("ADMIN")
def create_invitation():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({"error": "A JSON object is required"}), 400

    role = data.get("role", "USER")
    email = data.get("email", "")

    if not isinstance(role, str) or role not in (
        "USER", "TECHNICIAN", "ADMIN"
    ):
        return jsonify({
            "error": "Invitation role must be USER, TECHNICIAN or ADMIN"
        }), 400

    if not isinstance(email, str):
        return jsonify({"error": "Email must be text"}), 400

    email = email.strip().lower()

    if email and (
        len(email) > 255
        or email.count("@") != 1
        or not all(email.split("@"))
        or any(character.isspace() for character in email)
    ):
        return jsonify({"error": "Enter a valid email address"}), 400

    code = secrets.token_urlsafe(32)

    invitation = Invitation(
        code_hash=hashlib.sha256(code.encode("utf-8")).hexdigest(),
        role=role,
        email=email or None,
        created_by_id=get_current_user().id,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=24)
    )

    db.session.add(invitation)
    db.session.commit()

    response = jsonify({
        "message": "Copy this code now. It cannot be displayed again.",
        "invitation": {
            "id": invitation.id,
            "code": code,
            "role": invitation.role,
            "email": invitation.email,
            "expires_at": invitation.expires_at.isoformat()
        }
    })
    response.headers["Cache-Control"] = "no-store"
    return response, 201


@auth.get("/invitations")
@role_required("ADMIN")
def list_invitations():
    invitations = (
        Invitation.query
        .order_by(Invitation.id.desc())
        .limit(100)
        .all()
    )

    now = datetime.now(timezone.utc)
    results = []

    for invitation in invitations:
        if invitation.used_at is not None:
            status = "USED"
        elif invitation.revoked_at is not None:
            status = "REVOKED"
        elif invitation.expires_at <= now:
            status = "EXPIRED"
        else:
            status = "ACTIVE"

        results.append({
            "id": invitation.id,
            "role": invitation.role,
            "email": invitation.email,
            "status": status,
            "created_at": invitation.created_at.isoformat(),
            "expires_at": invitation.expires_at.isoformat()
        })

    response = jsonify(results)
    response.headers["Cache-Control"] = "no-store"
    return response, 200


@auth.post("/invitations/<int:invitation_id>/revoke")
@role_required("ADMIN")
def revoke_invitation(invitation_id):
    invitation = (
        Invitation.query
        .filter_by(id=invitation_id)
        .populate_existing()
        .with_for_update()
        .first()
    )

    if invitation is None:
        db.session.rollback()
        return jsonify({"error": "Invitation not found"}), 404

    if invitation.used_at is not None:
        db.session.rollback()
        return jsonify({"error": "Invitation has already been used"}), 409

    if invitation.revoked_at is None:
        invitation.revoked_at = datetime.now(timezone.utc)

    db.session.commit()

    return jsonify({"message": "Invitation revoked"}), 200
@auth.post("/setup/initial-admin")
def setup_initial_admin():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({
            "error": "A JSON object is required"
        }), 400
    setup_token = data.get("setup_token", "")
    expected_token = current_app.config.get(
        "INITIAL_SETUP_TOKEN"
    )

    if not isinstance(setup_token, str):
        return jsonify({
            "error": "Setup token must be text"
        }), 400

    if not expected_token:
        return jsonify({
            "error": "Initial setup is not configured"
        }), 503

    if not secrets.compare_digest(
        setup_token,
        expected_token
    ):
        return jsonify({
            "error": "Invalid setup token"
        }), 403

    username = data.get("username", "")
    email = data.get("email", "")
    password = data.get("password", "")

    if not all(
        isinstance(value, str)
        for value in (username, email, password)
    ):
        return jsonify({
            "error": "Username, email and password are required"
        }), 400

    username = username.strip()
    email = email.strip().lower()

    if not username or not email or not password:
        return jsonify({
            "error": "Username, email and password are required"
        }), 400

    if len(username) > 100 or len(email) > 255:
        return jsonify({
            "error": "Username or email is too long"
        }), 400

    if (
        email.count("@") != 1
        or not all(email.split("@"))
        or any(character.isspace() for character in email)
    ):
        return jsonify({
            "error": "Enter a valid email address"
        }), 400

    if not 8 <= len(password) <= 128:
        return jsonify({
            "error": "Password must be between 8 and 128 characters"
        }), 400

    if User.query.filter_by(role="ADMIN").first():
        return jsonify({
            "error": "Initial setup has already been completed"
        }), 403

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
        role="ADMIN"
    )
    user.set_password(password)

    try:
        db.session.add(user)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({
            "error": "Unable to create the administrator account"
        }), 409

    session["user_id"] = user.id

    return jsonify({
        "message": "Initial administrator account created",
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role
        }
    }), 201
