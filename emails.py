import sqlite3
from flask import render_template, request, jsonify
from datetime import datetime
from config import DATABASE
from security import login_required
import re
import hashlib
import secrets
import pandas as pd

def register_emails_routes(app):

    @app.route('/emails')
    @login_required
    def emails():
        return render_template('emails.html')

    @app.route('/api/emails', methods=['GET', 'POST'])
    @login_required
    def api_emails():
        if request.method == 'GET':
            conn = sqlite3.connect(DATABASE)
            cursor = conn.cursor()
            cursor.execute("SELECT id, email, token, created_at FROM emails ORDER BY id DESC")
            rows = cursor.fetchall()
            conn.close()

            base_url = request.host_url.rstrip('/')

            return jsonify([
                {
                    "id": r[0],
                    "email": r[1],
                    "token": r[2],
                    "tracking_link": f"{base_url}/track/{r[2]}",
                    "created_at": r[3]
                } for r in rows
            ])

        emails_text = request.json.get('emails', '')
        if not emails_text:
            return jsonify({"error": "Список email пуст"}), 400

        email_list = []
        for line in emails_text.split('\n'):
            for email in line.split(','):
                email = email.strip()
                if email:
                    email_list.append(email)

        email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')

        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()

        added, skipped, errors = 0, 0, []

        for email in email_list:
            if not email_pattern.match(email):
                skipped += 1
                errors.append(f"Неверный формат: {email}")
                continue

            token = hashlib.md5(
                f"{email}_{secrets.token_hex(8)}_{datetime.now().timestamp()}".encode()
            ).hexdigest()[:16]

            try:
                cursor.execute(
                    "INSERT INTO emails (email, token, created_at) VALUES (?, ?, ?)",
                    (email.lower(), token, datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                )
                added += 1
            except sqlite3.IntegrityError:
                skipped += 1
                errors.append(f"Дубликат: {email}")

        conn.commit()
        conn.close()

        return jsonify({
            "status": "ok",
            "added": added,
            "skipped": skipped,
            "errors": errors
        })

    @app.route('/api/emails/delete', methods=['POST'])
    @login_required
    def api_emails_delete():
        ids = request.json.get('ids', [])
        if not ids:
            return jsonify({"error": "Не выбраны email"}), 400

        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute(
            f"DELETE FROM emails WHERE id IN ({','.join('?' * len(ids))})",
            ids
        )
        conn.commit()
        conn.close()

        return jsonify({"status": "ok"})
