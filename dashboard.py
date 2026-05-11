from flask import render_template
from security import login_required
from mail_accounts_api import register_mail_accounts_routes
from mail_sender_api import register_mail_sender_routes

def register_dashboard_routes(app):

    @app.route('/')
    @login_required
    def dashboard():
        return render_template('dashboard.html')

    @app.route('/analytics')
    @login_required
    def analytics():
        return render_template('analytics.html')
    
    # Регистрируем маршруты для почтовых учетных записей
    register_mail_accounts_routes(app)
    
    # Регистрируем маршруты для отправки писем
    register_mail_sender_routes(app)
