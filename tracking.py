import sqlite3
from flask import request, redirect
from datetime import datetime
from config import DATABASE

def register_tracking_routes(app):

    @app.route('/track/<token>')
    def track(token):
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()

        # Пытаемся найти email по токену
        cursor.execute(
            "SELECT id FROM emails WHERE token = ?",
            (token,)
        )
        row = cursor.fetchone()
        email_id = row[0] if row else None

        cursor.execute(
            """
            INSERT INTO clicks (timestamp, ip, user_agent, token, email_id)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                request.remote_addr,
                request.headers.get('User-Agent', 'unknown'),
                token,
                email_id
            )
        )

        conn.commit()
        conn.close()

        return redirect('https://ya.ru')
