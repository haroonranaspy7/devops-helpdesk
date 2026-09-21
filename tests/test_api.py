import pytest

from app import create_app, db
from app.models.user import User
from app.models.ticket import Ticket

@pytest.fixture
def app():
    app = create_app(testing=True)

    with app.app_context():
        db.drop_all()
        db.create_all()

        yield app

        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def authenticated_client(client):
    # Create test user
    response = client.post(
        "/auth/register",
        json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "TestPassword123"
        }
    )

    assert response.status_code == 201

    # Login
    response = client.post(
        "/auth/login",
        json={
            "email": "test@example.com",
            "password": "TestPassword123"
        }
    )

    assert response.status_code == 200

    return client


def test_health(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.get_json()["status"] == "healthy"


def test_create_ticket(authenticated_client):
    response = authenticated_client.post(
        "/tickets",
        json={
            "title": "Test ticket",
            "description": "This ticket was created by pytest.",
            "priority": "HIGH"
        }
    )

    assert response.status_code == 201

    data = response.get_json()

    assert data["message"] == "Ticket created successfully"
    assert "ticket_id" in data


def test_create_ticket_invalid_priority(authenticated_client):
    response = authenticated_client.post(
        "/tickets",
        json={
            "title": "Invalid priority test",
            "description": "This should fail validation.",
            "priority": "BANANA"
        }
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "Invalid priority"


def test_create_ticket_requires_authentication(client):
    response = client.post(
        "/tickets",
        json={
            "title": "Unauthorized ticket",
            "description": "This should not be allowed.",
            "priority": "HIGH"
        }
    )

    assert response.status_code == 401
    assert response.get_json()["error"] == "Authentication required"
def test_user_can_update_own_ticket(authenticated_client):
    response = authenticated_client.post(
        "/tickets",
        json={
            "title": "Original title",
            "description": "Original description",
            "priority": "MEDIUM"
        }
    )

    assert response.status_code == 201

    ticket_id = response.get_json()["ticket_id"]

    response = authenticated_client.patch(
        f"/tickets/{ticket_id}",
        json={
            "title": "Updated title",
            "description": "Updated description"
        }
    )

    assert response.status_code == 200
    assert response.get_json()["message"] == "Ticket updated successfully"
def test_technician_can_update_assigned_ticket(authenticated_client, app):
    # Create a ticket as the normal USER
    response = authenticated_client.post(
        "/tickets",
        json={
            "title": "Technician test ticket",
            "description": "Testing technician permissions.",
            "priority": "MEDIUM"
        }
    )

    assert response.status_code == 201

    ticket_id = response.get_json()["ticket_id"]

    # Change the logged-in user's role to TECHNICIAN
    # and assign the ticket to that technician.
    with app.app_context():
        user = User.query.filter_by(
            email="test@example.com"
        ).first()

        user.role = "TECHNICIAN"

        ticket = db.session.get(
            Ticket,
            ticket_id
        )

        ticket.assigned_to_id = user.id

        db.session.commit()

    # Technician should now be able to update
    # the ticket because it is assigned to them.
    response = authenticated_client.patch(
        f"/tickets/{ticket_id}",
        json={
            "status": "IN_PROGRESS"
        }
    )

    assert response.status_code == 200
    assert response.get_json()["message"] == "Ticket updated successfully"
def test_technician_can_update_user_ticket_with_separate_session(client, app):
    # Create the normal user
    response = client.post(
        "/auth/register",
        json={
            "username": "user1",
            "email": "user1@example.com",
            "password": "UserPassword123"
        }
    )
    assert response.status_code == 201

    # Log in as the normal user
    response = client.post(
        "/auth/login",
        json={
            "email": "user1@example.com",
            "password": "UserPassword123"
        }
    )
    assert response.status_code == 200

    # Create a ticket
    response = client.post(
        "/tickets",
        json={
            "title": "User ticket",
            "description": "Needs technician assistance.",
            "priority": "HIGH"
        }
    )
    assert response.status_code == 201
    ticket_id = response.get_json()["ticket_id"]

    # Log out the user
    response = client.post("/auth/logout")
    assert response.status_code == 200

    # Create a separate technician account
    response = client.post(
        "/auth/register",
        json={
            "username": "technician1",
            "email": "technician@example.com",
            "password": "TechPassword123"
        }
    )
    assert response.status_code == 201

    # Change technician's role to TECHNICIAN
    with app.app_context():
        technician = User.query.filter_by(
            email="technician@example.com"
        ).first()
        technician.role = "TECHNICIAN"
        db.session.commit()

    # Log in as technician
    response = client.post(
    "/auth/login",
    json={
        "email": "technician@example.com",
        "password": "TechPassword123"
    }
    )
    assert response.status_code == 200

    # Assign the ticket to the technician
    with app.app_context():
        technician = User.query.filter_by(
            email="technician@example.com"
        ).first()

        ticket = db.session.get(Ticket, ticket_id)
        ticket.assigned_to_id = technician.id
        db.session.commit()

    # Technician attempts to update the user's ticket
    response = client.patch(
        f"/tickets/{ticket_id}",
        json={"status": "IN_PROGRESS"}
    )

    assert response.status_code == 200
    assert response.get_json()["message"] == "Ticket updated successfully"

def test_user_cannot_update_other_users_ticket(client):
    # Create first user
    response = client.post(
        "/auth/register",
        json={
            "username": "user1",
            "email": "user1@example.com",
            "password": "TestPassword123"
        }
    )
    assert response.status_code == 201

    # Login as first user
    response = client.post(
        "/auth/login",
        json={
            "email": "user1@example.com",
            "password": "TestPassword123"
        }
    )
    assert response.status_code == 200

    # Create ticket as first user
    response = client.post(
        "/tickets",
        json={
            "title": "Private ticket",
            "description": "This belongs to user1",
            "priority": "MEDIUM"
        }
    )
    assert response.status_code == 201

    ticket_id = response.get_json()["ticket_id"]

    # Logout first user
    response = client.post("/auth/logout")
    assert response.status_code == 200

    # Create second user
    response = client.post(
        "/auth/register",
        json={
            "username": "user2",
            "email": "user2@example.com",
            "password": "TestPassword123"
        }
    )
    assert response.status_code == 201

    # Login as second user
    response = client.post(
        "/auth/login",
        json={
            "email": "user2@example.com",
            "password": "TestPassword123"
        }
    )
    assert response.status_code == 200

    # Try to update user1's ticket
    response = client.patch(
        f"/tickets/{ticket_id}",
        json={
            "title": "Hacked title"
        }
    )

    assert response.status_code == 403
    assert response.get_json()["error"] == "Access denied"
def test_user_cannot_change_ticket_status(authenticated_client):
    response = authenticated_client.post(
        "/tickets",
        json={
            "title": "Test ticket",
            "description": "Testing status permissions",
            "priority": "MEDIUM"
        }
    )
    assert response.status_code == 201

    ticket_id = response.get_json()["ticket_id"]

    response = authenticated_client.patch(
        f"/tickets/{ticket_id}",
        json={
            "status": "IN_PROGRESS"
        }
    )

    assert response.status_code == 403
    assert response.get_json()["error"] == (
        "Users can only edit title and description"
    )
def test_user_cannot_change_ticket_priority(authenticated_client):
    response = authenticated_client.post(
        "/tickets",
        json={
            "title": "Test ticket",
            "description": "Testing priority permissions",
            "priority": "MEDIUM"
        }
    )
    assert response.status_code == 201

    ticket_id = response.get_json()["ticket_id"]

    response = authenticated_client.patch(
        f"/tickets/{ticket_id}",
        json={
            "priority": "CRITICAL"
        }
    )

    assert response.status_code == 403
    assert response.get_json()["error"] == (
        "Users can only edit title and description"
    )
def test_user_cannot_assign_ticket(authenticated_client, app):
    response = authenticated_client.post(
        "/tickets",
        json={
            "title": "Assignment test",
            "description": "Testing assignment permissions",
            "priority": "MEDIUM"
        }
    )
    assert response.status_code == 201

    ticket_id = response.get_json()["ticket_id"]

    # Create a technician
    authenticated_client.post(
        "/auth/logout"
    )

    response = authenticated_client.post(
        "/auth/register",
        json={
            "username": "technician1",
            "email": "technician1@example.com",
            "password": "TestPassword123"
        }
    )
    assert response.status_code == 201

    # Promote the user to TECHNICIAN for this test
    with app.app_context():
        technician = User.query.filter_by(
            email="technician1@example.com"
        ).first()
        technician.role = "TECHNICIAN"
        technician_id = technician.id
        db.session.commit()

    # Log back in as the original USER
    authenticated_client.post(
        "/auth/login",
        json={
            "email": "test@example.com",
            "password": "TestPassword123"
        }
    )

    response = authenticated_client.patch(
        f"/tickets/{ticket_id}",
        json={
            "assigned_to_id": technician_id
        }
    )

    assert response.status_code == 403
    assert response.get_json()["error"] == (
        "Users can only edit title and description"
    )
def test_technician_cannot_update_unassigned_ticket(client, app):
    # Create user
    response = client.post(
        "/auth/register",
        json={
            "username": "ticketowner",
            "email": "owner@example.com",
            "password": "TestPassword123"
        }
    )
    assert response.status_code == 201

    # Login as user
    response = client.post(
        "/auth/login",
        json={
            "email": "owner@example.com",
            "password": "TestPassword123"
        }
    )
    assert response.status_code == 200

    # Create ticket
    response = client.post(
        "/tickets",
        json={
            "title": "Unassigned ticket",
            "description": "This ticket belongs to another user",
            "priority": "MEDIUM"
        }
    )
    assert response.status_code == 201

    ticket_id = response.get_json()["ticket_id"]

    # Logout
    client.post("/auth/logout")

    # Create technician
    response = client.post(
        "/auth/register",
        json={
            "username": "technician2",
            "email": "technician2@example.com",
            "password": "TestPassword123"
        }
    )
    assert response.status_code == 201

    # Promote to TECHNICIAN
    with app.app_context():
        technician = User.query.filter_by(
            email="technician2@example.com"
        ).first()
        technician.role = "TECHNICIAN"
        technician_id = technician.id
        db.session.commit()

    # Login as technician
    response = client.post(
        "/auth/login",
        json={
            "email": "technician2@example.com",
            "password": "TestPassword123"
        }
    )
    assert response.status_code == 200

    # Technician tries to update a ticket not assigned to them
    response = client.patch(
        f"/tickets/{ticket_id}",
        json={
            "status": "IN_PROGRESS"
        }
    )

    assert response.status_code == 403
    assert response.get_json()["error"] == "Access denied"
def test_admin_can_assign_ticket_to_technician(client, app):
    # Create ticket owner
    response = client.post(
        "/auth/register",
        json={
            "username": "ticketowner",
            "email": "admin_test_owner@example.com",
            "password": "TestPassword123"
        }
    )
    assert response.status_code == 201

    # Login as ticket owner
    response = client.post(
        "/auth/login",
        json={
            "email": "admin_test_owner@example.com",
            "password": "TestPassword123"
        }
    )
    assert response.status_code == 200

    # Create ticket
    response = client.post(
        "/tickets",
        json={
            "title": "Admin assignment test",
            "description": "Testing admin ticket assignment",
            "priority": "HIGH"
        }
    )
    assert response.status_code == 201

    ticket_id = response.get_json()["ticket_id"]

    # Logout owner
    response = client.post("/auth/logout")
    assert response.status_code == 200

    # Create technician
    response = client.post(
        "/auth/register",
        json={
            "username": "assignmenttech",
            "email": "assignmenttech@example.com",
            "password": "TestPassword123"
        }
    )
    assert response.status_code == 201

    # Promote to TECHNICIAN
    with app.app_context():
        technician = User.query.filter_by(
            email="assignmenttech@example.com"
        ).first()
        technician.role = "TECHNICIAN"
        technician_id = technician.id
        db.session.commit()

    # Create admin
    response = client.post(
        "/auth/register",
        json={
            "username": "admin1",
            "email": "admin1@example.com",
            "password": "TestPassword123"
        }
    )
    assert response.status_code == 201

    # Promote to ADMIN
    with app.app_context():
        admin = User.query.filter_by(
            email="admin1@example.com"
        ).first()
        admin.role = "ADMIN"
        db.session.commit()

    # Login as admin
    response = client.post(
        "/auth/login",
        json={
            "email": "admin1@example.com",
            "password": "TestPassword123"
        }
    )
    assert response.status_code == 200

    # Admin assigns ticket to technician
    response = client.patch(
        f"/tickets/{ticket_id}",
        json={
            "assigned_to_id": technician_id
        }
    )

    assert response.status_code == 200
    assert response.get_json()["message"] == "Ticket updated successfully"

    # Verify assignment in database
    with app.app_context():
        ticket = db.session.get(Ticket, ticket_id)
        assert ticket.assigned_to_id == technician_id
def test_technician_can_view_assigned_tickets(client, app):
    # Create ticket owner
    response = client.post(
        "/auth/register",
        json={
            "username": "viewowner",
            "email": "viewowner@example.com",
            "password": "TestPassword123"
        }
    )
    assert response.status_code == 201

    # Login as owner
    response = client.post(
        "/auth/login",
        json={
            "email": "viewowner@example.com",
            "password": "TestPassword123"
        }
    )
    assert response.status_code == 200

    # Create ticket
    response = client.post(
        "/tickets",
        json={
            "title": "Technician view test",
            "description": "Technician should see this",
            "priority": "HIGH"
        }
    )
    assert response.status_code == 201

    ticket_id = response.get_json()["ticket_id"]

    # Logout owner
    response = client.post("/auth/logout")
    assert response.status_code == 200

    # Create technician
    response = client.post(
        "/auth/register",
        json={
            "username": "viewtechnician",
            "email": "viewtechnician@example.com",
            "password": "TestPassword123"
        }
    )
    assert response.status_code == 201

    # Promote to TECHNICIAN and assign the ticket
    with app.app_context():
        technician = User.query.filter_by(
            email="viewtechnician@example.com"
        ).first()
        technician.role = "TECHNICIAN"
        technician_id = technician.id

        ticket = db.session.get(Ticket, ticket_id)
        ticket.assigned_to_id = technician_id

        db.session.commit()

    # Login as technician
    response = client.post(
        "/auth/login",
        json={
            "email": "viewtechnician@example.com",
            "password": "TestPassword123"
        }
    )
    assert response.status_code == 200

    # Technician requests ticket list
    response = client.get("/tickets")

    assert response.status_code == 200

    tickets = response.get_json()

    assert len(tickets) == 1
    assert tickets[0]["id"] == ticket_id
    assert tickets[0]["assigned_to"]["id"] == technician_id
def test_admin_can_view_all_tickets(client, app):
    # Create first user
    response = client.post(
        "/auth/register",
        json={
            "username": "adminowner1",
            "email": "adminowner1@example.com",
            "password": "TestPassword123"
        }
    )
    assert response.status_code == 201

    # Login as first user
    client.post(
        "/auth/login",
        json={
            "email": "adminowner1@example.com",
            "password": "TestPassword123"
        }
    )

    # Create first ticket
    response = client.post(
        "/tickets",
        json={
            "title": "Admin ticket 1",
            "description": "First ticket",
            "priority": "MEDIUM"
        }
    )
    assert response.status_code == 201

    client.post("/auth/logout")

    # Create second user
    response = client.post(
        "/auth/register",
        json={
            "username": "adminowner2",
            "email": "adminowner2@example.com",
            "password": "TestPassword123"
        }
    )
    assert response.status_code == 201

    # Login as second user
    client.post(
        "/auth/login",
        json={
            "email": "adminowner2@example.com",
            "password": "TestPassword123"
        }
    )

    # Create second ticket
    response = client.post(
        "/tickets",
        json={
            "title": "Admin ticket 2",
            "description": "Second ticket",
            "priority": "HIGH"
        }
    )
    assert response.status_code == 201

    client.post("/auth/logout")

    # Create admin
    response = client.post(
        "/auth/register",
        json={
            "username": "viewadmin",
            "email": "viewadmin@example.com",
            "password": "TestPassword123"
        }
    )
    assert response.status_code == 201

    # Promote to ADMIN
    with app.app_context():
        admin = User.query.filter_by(
            email="viewadmin@example.com"
        ).first()
        admin.role = "ADMIN"
        db.session.commit()

    # Login as admin
    response = client.post(
        "/auth/login",
        json={
            "email": "viewadmin@example.com",
            "password": "TestPassword123"
        }
    )
    assert response.status_code == 200

    # Admin requests all tickets
    response = client.get("/tickets")

    assert response.status_code == 200

    tickets = response.get_json()

    assert len(tickets) == 2
def test_technician_can_view_assigned_ticket(client, app):
    # Create ticket owner
    response = client.post(
        "/auth/register",
        json={
            "username": "singleowner",
            "email": "singleowner@example.com",
            "password": "TestPassword123"
        }
    )
    assert response.status_code == 201

    # Login as owner
    client.post(
        "/auth/login",
        json={
            "email": "singleowner@example.com",
            "password": "TestPassword123"
        }
    )

    # Create ticket
    response = client.post(
        "/tickets",
        json={
            "title": "Single ticket access",
            "description": "Technician should be able to view this",
            "priority": "HIGH"
        }
    )
    assert response.status_code == 201

    ticket_id = response.get_json()["ticket_id"]

    client.post("/auth/logout")

    # Create technician
    response = client.post(
        "/auth/register",
        json={
            "username": "singletech",
            "email": "singletech@example.com",
            "password": "TestPassword123"
        }
    )
    assert response.status_code == 201

    # Promote technician and assign ticket
    with app.app_context():
        technician = User.query.filter_by(
            email="singletech@example.com"
        ).first()

        technician.role = "TECHNICIAN"
        technician_id = technician.id

        ticket = db.session.get(Ticket, ticket_id)
        ticket.assigned_to_id = technician_id

        db.session.commit()

    # Login as technician
    response = client.post(
        "/auth/login",
        json={
            "email": "singletech@example.com",
            "password": "TestPassword123"
        }
    )
    assert response.status_code == 200

    # View the assigned ticket
    response = client.get(f"/tickets/{ticket_id}")

    assert response.status_code == 200

    ticket_data = response.get_json()

    assert ticket_data["id"] == ticket_id
    assert ticket_data["assigned_to"]["id"] == technician_id
def test_technician_can_view_unassigned_ticket(client, app):
    # Create ticket owner
    response = client.post(
        "/auth/register",
        json={
            "username": "viewowner",
            "email": "viewowner@example.com",
            "password": "TestPassword123"
        }
    )
    assert response.status_code == 201

    # Login as owner
    response = client.post(
        "/auth/login",
        json={
            "email": "viewowner@example.com",
            "password": "TestPassword123"
        }
    )
    assert response.status_code == 200

    # Create ticket
    response = client.post(
        "/tickets",
        json={
            "title": "Unassigned ticket",
            "description": "Technician should be able to view this",
            "priority": "HIGH"
        }
    )
    assert response.status_code == 201

    ticket_id = response.get_json()["ticket_id"]

    client.post("/auth/logout")

    # Create technician
    response = client.post(
        "/auth/register",
        json={
            "username": "viewtech",
            "email": "viewtech@example.com",
            "password": "TestPassword123"
        }
    )
    assert response.status_code == 201

    # Promote user to technician
    with app.app_context():
        technician = User.query.filter_by(
            email="viewtech@example.com"
        ).first()

        technician.role = "TECHNICIAN"
        db.session.commit()

        technician_id = technician.id

    # Login as technician
    response = client.post(
        "/auth/login",
        json={
            "email": "viewtech@example.com",
            "password": "TestPassword123"
        }
    )
    assert response.status_code == 200

    # Technician views a ticket that is not assigned to them.
    response = client.get(f"/tickets/{ticket_id}")

    assert response.status_code == 200

    ticket_data = response.get_json()

    assert ticket_data["id"] == ticket_id
    assert ticket_data["title"] == "Unassigned ticket"
    assert ticket_data["assigned_to"] is None
def test_user_cannot_delete_ticket(authenticated_client):
    response = authenticated_client.post(
        "/tickets",
        json={
            "title": "Delete authorization test",
            "description": "User should not delete this ticket.",
            "priority": "MEDIUM"
        }
    )

    assert response.status_code == 201

    ticket_id = response.get_json()["ticket_id"]

    response = authenticated_client.delete(
        f"/tickets/{ticket_id}"
    )

    assert response.status_code == 403

    assert response.get_json()["error"] == (
        "Only administrators can delete tickets"
    )


def test_admin_can_delete_ticket(client, app):
    response = client.post(
        "/auth/register",
        json={
            "username": "admin",
            "email": "admin@example.com",
            "password": "AdminPassword123"
        }
    )

    assert response.status_code == 201

    with app.app_context():
        admin = User.query.filter_by(
            email="admin@example.com"
        ).first()

        admin.role = "ADMIN"

        db.session.commit()

    response = client.post(
        "/auth/login",
        json={
            "email": "admin@example.com",
            "password": "AdminPassword123"
        }
    )

    assert response.status_code == 200

    response = client.post(
        "/tickets",
        json={
            "title": "Admin delete test",
            "description": "Admin should be able to delete this.",
            "priority": "MEDIUM"
        }
    )

    assert response.status_code == 201

    ticket_id = response.get_json()["ticket_id"]

    response = client.delete(
        f"/tickets/{ticket_id}"
    )

    assert response.status_code == 200

    data = response.get_json()

    assert data["message"] == "Ticket deleted successfully"
    assert data["ticket_id"] == ticket_id
def create_admin(client, app):
    response = client.post(
        "/auth/register",
        json={
            "username": "testadmin",
            "email": "testadmin@example.com",
            "password": "AdminPassword123"
        }
    )

    assert response.status_code == 201

    with app.app_context():
        admin = User.query.filter_by(
            email="testadmin@example.com"
        ).first()

        admin.role = "ADMIN"

        db.session.commit()

    response = client.post(
        "/auth/login",
        json={
            "email": "testadmin@example.com",
            "password": "AdminPassword123"
        }
    )

    assert response.status_code == 200


def test_admin_can_list_users(client, app):
    create_admin(client, app)

    response = client.post(
        "/auth/register",
        json={
            "username": "normaluser",
            "email": "normaluser@example.com",
            "password": "UserPassword123"
        }
    )

    assert response.status_code == 201

    response = client.get("/admin/users")

    assert response.status_code == 200

    users = response.get_json()

    assert len(users) == 2

    usernames = {
        user["username"]
        for user in users
    }

    assert "testadmin" in usernames
    assert "normaluser" in usernames


def test_non_admin_cannot_list_users(authenticated_client):
    response = authenticated_client.get("/admin/users")

    assert response.status_code == 403
    assert response.get_json()["error"] == (
        "Insufficient permissions"
    )


def test_admin_can_create_technician(client, app):
    create_admin(client, app)

    response = client.post(
        "/admin/users",
        json={
            "username": "newtechnician",
            "email": "newtechnician@example.com",
            "password": "TechPassword123",
            "role": "TECHNICIAN"
        }
    )

    assert response.status_code == 201

    data = response.get_json()

    assert data["user"]["username"] == "newtechnician"
    assert data["user"]["role"] == "TECHNICIAN"

    with app.app_context():
        user = User.query.filter_by(
            email="newtechnician@example.com"
        ).first()

        assert user is not None
        assert user.role == "TECHNICIAN"
        assert user.check_password("TechPassword123")


def test_admin_can_create_admin(client, app):
    create_admin(client, app)

    response = client.post(
        "/admin/users",
        json={
            "username": "secondadmin",
            "email": "secondadmin@example.com",
            "password": "AdminPassword123",
            "role": "ADMIN"
        }
    )

    assert response.status_code == 201

    data = response.get_json()

    assert data["user"]["role"] == "ADMIN"


def test_admin_rejects_invalid_role(client, app):
    create_admin(client, app)

    response = client.post(
        "/admin/users",
        json={
            "username": "badrole",
            "email": "badrole@example.com",
            "password": "TestPassword123",
            "role": "SUPERUSER"
        }
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "Invalid role"


def test_admin_rejects_duplicate_user(client, app):
    create_admin(client, app)

    response = client.post(
        "/admin/users",
        json={
            "username": "duplicate",
            "email": "duplicate@example.com",
            "password": "TestPassword123",
            "role": "USER"
        }
    )

    assert response.status_code == 201

    response = client.post(
        "/admin/users",
        json={
            "username": "duplicate",
            "email": "another@example.com",
            "password": "TestPassword123",
            "role": "USER"
        }
    )

    assert response.status_code == 409
    assert response.get_json()["error"] == (
        "Username already exists"
    )


def test_admin_can_change_user_role(client, app):
    create_admin(client, app)

    response = client.post(
        "/admin/users",
        json={
            "username": "rolechange",
            "email": "rolechange@example.com",
            "password": "TestPassword123",
            "role": "USER"
        }
    )

    assert response.status_code == 201

    user_id = response.get_json()["user"]["id"]

    response = client.patch(
        f"/admin/users/{user_id}",
        json={
            "role": "TECHNICIAN"
        }
    )

    assert response.status_code == 200

    data = response.get_json()

    assert data["user"]["role"] == "TECHNICIAN"

    with app.app_context():
        user = db.session.get(User, user_id)

        assert user.role == "TECHNICIAN"


def test_admin_cannot_change_own_role(client, app):
    create_admin(client, app)

    with app.app_context():
        admin = User.query.filter_by(
            email="testadmin@example.com"
        ).first()

        admin_id = admin.id

    response = client.patch(
        f"/admin/users/{admin_id}",
        json={
            "role": "USER"
        }
    )

    assert response.status_code == 403

    assert response.get_json()["error"] == (
        "Administrators cannot change their own role"
    )
