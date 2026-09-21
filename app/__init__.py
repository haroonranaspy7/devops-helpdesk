import os

from flask import Flask
from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()


def create_app(testing=False):
    app = Flask(
        __name__,
        static_folder="../static",
        template_folder="templates",
    )

    if testing:
        database_url = os.getenv(
            "TEST_DATABASE_URL",
            (
                "postgresql+psycopg://"
                "helpdesk_user:helpdesk_dev_password"
                "@localhost:5432/helpdesk_test_db"
            ),
        )
    else:
        database_url = os.getenv(
            "DATABASE_URL",
            (
                "postgresql+psycopg://"
                "helpdesk_user:helpdesk_dev_password"
                "@localhost:5432/helpdesk_db"
            ),
        )

    app.config["SQLALCHEMY_DATABASE_URI"] = database_url

    app.config["SECRET_KEY"] = os.getenv(
        "SECRET_KEY",
        "dev-secret-key-change-me",
    )

    db.init_app(app)

    from app.auth import auth
    from app.routes import api

    app.register_blueprint(auth)
    app.register_blueprint(api)

    return app
