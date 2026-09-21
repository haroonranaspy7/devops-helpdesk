#!/bin/sh

set -e

echo "Initializing database tables..."

python - <<'PYTHON'
from app import create_app, db

application = create_app()

with application.app_context():
    db.create_all()
PYTHON

echo "Starting IT Helpdesk Platform..."

exec gunicorn \
    --bind 0.0.0.0:5000 \
    --workers 2 \
    --threads 4 \
    --timeout 60 \
    run:app
