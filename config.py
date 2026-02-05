import os
from datetime import timedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, 'phishing_data.db')

SECRET_KEY = 'phishing-dashboard-2026-super-secret-key'

IDLE_TIMEOUT_MINUTES = 15
PERMANENT_SESSION_LIFETIME = timedelta(minutes=IDLE_TIMEOUT_MINUTES)

SESSION_CONFIG = {
    "SESSION_COOKIE_HTTPONLY": True,
    "SESSION_COOKIE_SAMESITE": "Lax",
    "SESSION_COOKIE_SECURE": False  # True при HTTPS
}
