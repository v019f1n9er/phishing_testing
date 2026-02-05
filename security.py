import secrets
from functools import wraps
from flask import session, request, redirect, url_for

def generate_csrf_token():
    if '_csrf_token' not in session:
        session['_csrf_token'] = secrets.token_hex(32)
    return session['_csrf_token']

def csrf_protect():
    if request.method == "POST":
        token = session.get('_csrf_token')
        form_token = (
            request.form.get('_csrf_token')
            or request.headers.get('X-CSRF-Token')
        )
        if not token or token != form_token:
            return "CSRF validation failed", 403

def session_timeout_check():
    if session.get('user_id'):
        session.permanent = True
        session.modified = True

def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get('user_id'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return wrapper
