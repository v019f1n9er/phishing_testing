import os
from datetime import timedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, 'phishing_data.db')

# По умолчанию, если переменные окружения отсутствуют
SECRET_KEY = os.environ.get(
    'SECRET_KEY', 'phishing-dashboard-2026-super-secret-key'
)

IDLE_TIMEOUT_MINUTES = 15
PERMANENT_SESSION_LIFETIME = timedelta(minutes=IDLE_TIMEOUT_MINUTES)

def _str_to_bool(v):
    if isinstance(v, bool):
        return v
    if v is None:
        return False
    return str(v).lower() in ("1", "true", "yes", "on")

SESSION_CONFIG = {
    "SESSION_COOKIE_HTTPONLY": True,
    "SESSION_COOKIE_SAMESITE": "Lax",
    # Читаем из переменной окружения SESSION_COOKIE_SECURE
    "SESSION_COOKIE_SECURE": _str_to_bool(os.environ.get('SESSION_COOKIE_SECURE', False))
}
