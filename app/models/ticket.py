from datetime import datetime, timezone

from app import db


class Ticket(db.Model):
    __tablename__ = "tickets"

    id = db.Column(db.Integer, primary_key=True)

    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)

    priority = db.Column(
        db.String(20),
        nullable=False,
        default="MEDIUM"
    )

    status = db.Column(
        db.String(20),
        nullable=False,
        default="OPEN"
    )

    created_by_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )

    assigned_to_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=True
    )

    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )

    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    created_by = db.relationship(
        "User",
        foreign_keys=[created_by_id],
        backref="created_tickets"
    )

    assigned_to = db.relationship(
        "User",
        foreign_keys=[assigned_to_id],
        backref="assigned_tickets"
    )
