import logging
from flask import Flask
from config import SECRET_KEY, SESSION_CONFIG, PERMANENT_SESSION_LIFETIME
from security import generate_csrf_token, csrf_protect, session_timeout_check
from db import initialize_db, initialize_users, initialize_emails

from auth import register_auth_routes
from api import register_api_routes
from tracking import register_tracking_routes
from dashboard import register_dashboard_routes
from emails import register_emails_routes
from db import (
    initialize_db,
    initialize_users,
    initialize_emails,
    migrate_clicks_add_email_id
)
from exports import register_export_routes

import logging

class IgnoreApiClicksFilter(logging.Filter):
    def filter(self, record):
        message = str(record.getMessage())
        for pattern in ['/api/clicks', '/api/emails', '/api/analytics']:
            if pattern in message:
                return False
        return True

def create_app():
    app = Flask(__name__)
    app.secret_key = SECRET_KEY
    app.permanent_session_lifetime = PERMANENT_SESSION_LIFETIME
    app.config.update(SESSION_CONFIG)

    app.jinja_env.globals['csrf_token'] = generate_csrf_token
    app.before_request(csrf_protect)
    app.before_request(session_timeout_check)

    register_auth_routes(app)
    register_api_routes(app)
    register_tracking_routes(app)
    register_dashboard_routes(app)
    register_emails_routes(app)
    register_export_routes(app)

    werkzeug_logger = logging.getLogger('werkzeug')
    werkzeug_logger.addFilter(IgnoreApiClicksFilter())
    werkzeug_logger.setLevel(logging.INFO)

    return app

if __name__ == '__main__':
    initialize_db()
    initialize_users()
    initialize_emails()
    migrate_clicks_add_email_id()

    app = create_app()
    app.run(host='0.0.0.0', port=8080, debug=False, use_reloader=False)
