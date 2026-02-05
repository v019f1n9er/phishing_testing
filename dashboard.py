from flask import render_template
from security import login_required

def register_dashboard_routes(app):

    @app.route('/')
    @login_required
    def dashboard():
        return render_template('dashboard.html')
