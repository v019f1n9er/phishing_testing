import sqlite3
from flask import render_template, request, session, redirect, url_for
from werkzeug.security import check_password_hash
from config import DATABASE

def register_auth_routes(app):

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            conn = sqlite3.connect(DATABASE)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, password_hash FROM users WHERE username = ?",
                (request.form.get('username'),)
            )
            user = cursor.fetchone()
            conn.close()

            if user and check_password_hash(user[1], request.form.get('password')):
                session.clear()
                session['user_id'] = user[0]
                return redirect(url_for('dashboard'))

            return render_template('login.html', error='Неверный логин или пароль')

        return render_template('login.html')

    @app.route('/logout')
    def logout():
        session.clear()
        return redirect(url_for('login'))
