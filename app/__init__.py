import os
import time

from flask import Flask, Response, request
from flask_sqlalchemy import SQLAlchemy
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Histogram,
    generate_latest
)

from app.logging_config import configure_logging


db = SQLAlchemy()


HTTP_REQUESTS_TOTAL = Counter(
    "helpdesk_http_requests_total",
    "Total number of HTTP requests received by the helpdesk application",
    [
        "method",
        "endpoint",
        "status"
    ]
)


HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "helpdesk_http_request_duration_seconds",
    "Time spent processing helpdesk HTTP requests",
    [
        "method",
        "endpoint"
    ]
)


def create_app(testing=False):
    configure_logging()

    app = Flask(
        __name__,
        static_folder="../static",
        template_folder="templates"
    )

    if testing:
        database_url = os.getenv(
            "TEST_DATABASE_URL",
            (
                "postgresql+psycopg://"
                "helpdesk_user:"
                "helpdesk_dev_password@"
                "localhost:5432/"
                "helpdesk_test_db"
            )
        )
    else:
        database_url = os.getenv(
            "DATABASE_URL",
            (
                "postgresql+psycopg://"
                "helpdesk_user:"
                "helpdesk_dev_password@"
                "localhost:5432/"
                "helpdesk_db"
            )
        )

    app.config[
        "SQLALCHEMY_DATABASE_URI"
    ] = database_url

    app.config["SECRET_KEY"] = os.getenv(
        "SECRET_KEY",
        "dev-secret-key-change-me"
    )
    app.config["INITIAL_SETUP_TOKEN"] = os.getenv(
        "INITIAL_SETUP_TOKEN"
    )

    db.init_app(app)

    from app.auth import auth
    from app.routes import api

    app.register_blueprint(api)
    app.register_blueprint(auth)

    @app.before_request
    def start_request_timer():
        request.prometheus_start_time = (
            time.perf_counter()
        )

    @app.after_request
    def record_request_observability(response):
        endpoint = (
            request.url_rule.rule
            if request.url_rule
            else "unmatched"
        )

        duration = (
            time.perf_counter() -
            request.prometheus_start_time
        )

        HTTP_REQUESTS_TOTAL.labels(
            method=request.method,
            endpoint=endpoint,
            status=response.status_code
        ).inc()

        HTTP_REQUEST_DURATION_SECONDS.labels(
            method=request.method,
            endpoint=endpoint
        ).observe(duration)

        app.logger.info(
            "http_request",
            extra={
                "event": "http_request",
                "method": request.method,
                "endpoint": endpoint,
                "path": request.path,
                "status": response.status_code,
                "duration_seconds": round(
                    duration,
                    6
                ),
                "remote_address": (
                    request.remote_addr
                )
            }
        )

        return response

    @app.get("/metrics")
    def metrics():
        return Response(
            generate_latest(),
            mimetype=CONTENT_TYPE_LATEST
        )

    return app
