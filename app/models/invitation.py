from datetime import datetime, timezone

from app import db


class Invitation(db.Model):
    __tablename__ = "invitations"

    __table_args__ = (
        db.CheckConstraint(
     "role IN ('USER', 'TECHNICIAN', 'ADMIN')",
            name="ck_invitation_role"
        ),
    )

    id = db.Column(db.Integer, primary_key=True)

    code_hash = db.Column(
        db.String(64),
        unique=True,
        nullable=False
    )

    role = db.Column(
        db.String(20),
        nullable=False
    )

    email = db.Column(
        db.String(255),
        nullable=True
    )

    created_by_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )

    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    expires_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False
    )

    used_at = db.Column(
        db.DateTime(timezone=True),
        nullable=True
    )

    revoked_at = db.Column(
        db.DateTime(timezone=True),
        nullable=True
    )
