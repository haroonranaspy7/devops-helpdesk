from flask import (
    Blueprint,
    jsonify,
    request,
    render_template,
    redirect,
    url_for
)
from sqlalchemy import text

from app import db
from app.models.user import User
from app.models.ticket import Ticket
from app.auth_utils import (
    login_required,
    get_current_user,
    role_required
)

api = Blueprint("api", __name__)


# ============================================================
# PAGE ROUTES
# ============================================================

@api.get("/dashboard")
def dashboard():
    return render_template("dashboard.html")

@api.get("/settings")
@login_required
def settings():
    return render_template("settings.html")

@api.get("/login")
def login_page():
    return render_template("login.html")

@api.get("/register")
def register_page():
    return render_template("register.html")

@api.get("/setup")
def setup_page():
    if User.query.filter_by(role="ADMIN").first():
        return redirect(url_for("api.login_page"))

    return render_template("setup.html")

# ============================================================
# BASIC / HEALTH ROUTES
# ============================================================

@api.get("/")
def home():
    return jsonify({
        "application": "IT Helpdesk Platform",
        "status": "running",
        "version": "1.0.0"
    })


@api.get("/health")
def health():
    return jsonify({
        "status": "healthy"
    })


@api.get("/db-test")
def db_test():
    result = db.session.execute(text("SELECT 1"))

    return jsonify({
        "database": "connected",
        "result": result.scalar()
    })

# ============================================================
# ADMIN USER MANAGEMENT
# ============================================================

@api.get("/admin/users")
@role_required("ADMIN")
def get_users():
    users = User.query.order_by(User.id.asc()).all()

    return jsonify([
        {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "created_at": (
                user.created_at.isoformat()
                if user.created_at
                else None
            )
        }
        for user in users
    ])


@api.post("/admin/users")
@role_required("ADMIN")
def create_user():
    data = request.get_json() or {}

    username = data.get("username", "").strip()
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")
    role = data.get("role", "USER")

    allowed_roles = {
        "USER",
        "TECHNICIAN",
        "ADMIN"
    }

    if not username or not email or not password:
        return jsonify({
            "error": "Username, email and password are required"
        }), 400

    if len(password) < 8:
        return jsonify({
            "error": "Password must be at least 8 characters"
        }), 400

    if role not in allowed_roles:
        return jsonify({
            "error": "Invalid role"
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
        role=role
    )

    user.set_password(password)

    db.session.add(user)
    db.session.commit()

    return jsonify({
        "message": "User created successfully",
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role
        }
    }), 201


@api.patch("/admin/users/<int:user_id>")
@role_required("ADMIN")
def update_user(user_id):
    user = db.session.get(User, user_id)

    if not user:
        return jsonify({
            "error": "User not found"
        }), 404

    current_user = get_current_user()
    data = request.get_json() or {}

    if current_user.id == user.id and "role" in data:
        return jsonify({
            "error": "Administrators cannot change their own role"
        }), 403

    if "role" in data:
        allowed_roles = {
            "USER",
            "TECHNICIAN",
            "ADMIN"
        }

        if data["role"] not in allowed_roles:
            return jsonify({
                "error": "Invalid role"
            }), 400

        user.role = data["role"]

    if "username" in data:
        username = data["username"].strip()

        if not username:
            return jsonify({
                "error": "Username cannot be empty"
            }), 400

        existing_user = User.query.filter(
            User.username == username,
            User.id != user.id
        ).first()

        if existing_user:
            return jsonify({
                "error": "Username already exists"
            }), 409

        user.username = username

    if "email" in data:
        email = data["email"].strip().lower()

        if not email:
            return jsonify({
                "error": "Email cannot be empty"
            }), 400

        existing_user = User.query.filter(
            User.email == email,
            User.id != user.id
        ).first()

        if existing_user:
            return jsonify({
                "error": "Email already exists"
            }), 409

        user.email = email

    db.session.commit()

    return jsonify({
        "message": "User updated successfully",
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role
        }
    }), 200

# ============================================================
# CREATE TICKET
# ============================================================

@api.post("/tickets")
@login_required
def create_ticket():
    data = request.get_json()

    if not data:
        return jsonify({
            "error": "Request body is required"
        }), 400

    # Title validation
    title = data.get("title")

    if not isinstance(title, str) or not title.strip():
        return jsonify({
            "error": "title is required"
        }), 400

    # Description validation
    description = data.get("description")

    if not isinstance(description, str) or not description.strip():
        return jsonify({
            "error": "description is required"
        }), 400

    # Priority validation
    allowed_priorities = {
        "LOW",
        "MEDIUM",
        "HIGH",
        "CRITICAL"
    }

    priority = data.get("priority", "MEDIUM")

    if priority not in allowed_priorities:
        return jsonify({
            "error": "Invalid priority"
        }), 400

    # The logged-in user is always the creator.
    # We do NOT trust created_by from the frontend.
    user = get_current_user()

    ticket = Ticket(
        title=title.strip(),
        description=description.strip(),
        priority=priority,
        status="OPEN",
        created_by=user
    )

    db.session.add(ticket)
    db.session.commit()

    return jsonify({
        "message": "Ticket created successfully",
        "ticket_id": ticket.id
    }), 201


# ============================================================
# GET ALL TICKETS
# ============================================================

@api.get("/tickets")
@login_required
def get_tickets():
    user = get_current_user()

    if user.role == "USER":

        tickets = Ticket.query.filter_by(
            created_by_id=user.id
        ).all()

    elif user.role == "TECHNICIAN":
        tickets = Ticket.query.all()
    elif user.role == "ADMIN":

        tickets = Ticket.query.all()

    else:

        return jsonify({
            "error": "Invalid user role"
        }), 403

    return jsonify([
        {
            "id": ticket.id,
            "title": ticket.title,
            "description": ticket.description,
            "priority": ticket.priority,
            "status": ticket.status,

            "created_by": {
                "id": ticket.created_by.id,
                "username": ticket.created_by.username
            },

            "assigned_to": (
                {
                    "id": ticket.assigned_to.id,
                    "username": ticket.assigned_to.username
                }
                if ticket.assigned_to
                else None
            ),

            "created_at": (
                ticket.created_at.isoformat()
                if ticket.created_at
                else None
            ),

            "updated_at": (
                ticket.updated_at.isoformat()
                if ticket.updated_at
                else None
            )
        }
        for ticket in tickets
    ])


# ============================================================
# GET SINGLE TICKET
# ============================================================

@api.get("/tickets/<int:ticket_id>")
@login_required
def get_ticket(ticket_id):
    ticket = db.session.get(Ticket, ticket_id)

    if not ticket:
        return jsonify({
            "error": "Ticket not found"
        }), 404

    user = get_current_user()

    # USER:
    # Can only see tickets they created.
    if user.role == "USER":
        if ticket.created_by_id != user.id:
            return jsonify({
                "error": "Access denied"
            }), 403

    elif user.role == "TECHNICIAN":
        pass

    elif user.role == "ADMIN":
        pass

    else:
        return jsonify({
            "error": "Invalid user role"
        }), 403

    return jsonify({
        "id": ticket.id,
        "title": ticket.title,
        "description": ticket.description,
        "priority": ticket.priority,
        "status": ticket.status,

        "created_by": {
            "id": ticket.created_by.id,
            "username": ticket.created_by.username
        },

        "assigned_to": (
            {
                "id": ticket.assigned_to.id,
                "username": ticket.assigned_to.username
            }
            if ticket.assigned_to
            else None
        ),

        "created_at": (
            ticket.created_at.isoformat()
            if ticket.created_at
            else None
        ),

        "updated_at": (
            ticket.updated_at.isoformat()
            if ticket.updated_at
            else None
        )
    })


# ============================================================
# UPDATE TICKET
# ============================================================

@api.patch("/tickets/<int:ticket_id>")
@login_required
def update_ticket(ticket_id):
    ticket = db.session.get(Ticket, ticket_id)

    if not ticket:
        return jsonify({
            "error": "Ticket not found"
        }), 404

    data = request.get_json()

    if not data:
        return jsonify({
            "error": "Request body is required"
        }), 400

    user = get_current_user()

    # --------------------------------------------------------
    # USER PERMISSIONS
    # --------------------------------------------------------

    if user.role == "USER":

        if ticket.created_by_id != user.id:
            return jsonify({
                "error": "Access denied"
            }), 403

        protected_fields = {
            "status",
            "priority",
            "assigned_to",
            "assigned_to_id"
        }

        if protected_fields.intersection(data.keys()):
            return jsonify({
                "error": "Users can only edit title and description"
            }), 403

    # --------------------------------------------------------
    # TECHNICIAN PERMISSIONS
    # --------------------------------------------------------

    elif user.role == "TECHNICIAN":

        if ticket.assigned_to_id != user.id:
            return jsonify({
                "error": "Access denied"
            }), 403

    # --------------------------------------------------------
    # ADMIN PERMISSIONS
    # --------------------------------------------------------

    elif user.role == "ADMIN":

        pass

    else:

        return jsonify({
            "error": "Invalid user role"
        }), 403

    # --------------------------------------------------------
    # VALID STATUS VALUES
    # --------------------------------------------------------

    allowed_statuses = {
        "OPEN",
        "IN_PROGRESS",
        "RESOLVED",
        "CLOSED"
    }

    # --------------------------------------------------------
    # VALID PRIORITY VALUES
    # --------------------------------------------------------

    allowed_priorities = {
        "LOW",
        "MEDIUM",
        "HIGH",
        "CRITICAL"
    }

    # --------------------------------------------------------
    # UPDATE STATUS
    # --------------------------------------------------------

    if "status" in data:

        if data["status"] not in allowed_statuses:
            return jsonify({
                "error": "Invalid status"
            }), 400

        ticket.status = data["status"]

    # --------------------------------------------------------
    # UPDATE PRIORITY
    # --------------------------------------------------------

    if "priority" in data:

        if data["priority"] not in allowed_priorities:
            return jsonify({
                "error": "Invalid priority"
            }), 400

        ticket.priority = data["priority"]

    # --------------------------------------------------------
    # UPDATE TITLE
    # --------------------------------------------------------

    if "title" in data:

        if (
            not isinstance(data["title"], str)
            or not data["title"].strip()
        ):
            return jsonify({
                "error": "title is required"
            }), 400

        ticket.title = data["title"].strip()

    # --------------------------------------------------------
    # UPDATE DESCRIPTION
    # --------------------------------------------------------

    if "description" in data:

        if (
            not isinstance(data["description"], str)
            or not data["description"].strip()
        ):
            return jsonify({
                "error": "description is required"
            }), 400

        ticket.description = data["description"].strip()

    # --------------------------------------------------------
    # ASSIGN TICKET
    # ADMIN ONLY
    # --------------------------------------------------------

    if "assigned_to_id" in data:

        if user.role != "ADMIN":
            return jsonify({
                "error": "Only administrators can assign tickets"
            }), 403

        assigned_user = db.session.get(
            User,
            data["assigned_to_id"]
        )

        if not assigned_user:
            return jsonify({
                "error": "Assigned user not found"
            }), 404

        if assigned_user.role != "TECHNICIAN":
            return jsonify({
                "error": "Tickets can only be assigned to technicians"
            }), 400

        ticket.assigned_to_id = assigned_user.id

    db.session.commit()

    return jsonify({
        "message": "Ticket updated successfully",
        "ticket_id": ticket.id
    }), 200


# ============================================================
# DELETE TICKET
# ADMIN ONLY
# ============================================================

@api.delete("/tickets/<int:ticket_id>")
@login_required
def delete_ticket(ticket_id):
    user = get_current_user()

    # Only administrators can delete tickets.
    if user.role != "ADMIN":
        return jsonify({
            "error": "Only administrators can delete tickets"
        }), 403

    ticket = db.session.get(Ticket, ticket_id)

    if not ticket:
        return jsonify({
            "error": "Ticket not found"
        }), 404

    db.session.delete(ticket)
    db.session.commit()

    return jsonify({
        "message": "Ticket deleted successfully",
        "ticket_id": ticket_id
    }), 200
@api.get("/admin/invitations")
@role_required("ADMIN")
def invitations_page():
    return render_template("invitations.html")
