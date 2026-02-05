import sqlite3
from flask import jsonify, request
from config import DATABASE
from security import login_required

def get_report_data():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            clicks.id,
            clicks.timestamp,
            clicks.ip,
            clicks.user_agent,
            clicks.token,
            clicks.email_id,
            emails.email
        FROM clicks
        LEFT JOIN emails ON emails.id = clicks.email_id
        ORDER BY clicks.id DESC
    """)

    rows = cursor.fetchall()
    conn.close()

    return [
        {
            "id": r[0],
            "timestamp": r[1],
            "ip": r[2],
            "user_agent": r[3],
            "token": r[4],
            "email_id": r[5],
            "email": r[6]
        }
        for r in rows
    ]

def register_api_routes(app):

    @app.route('/api/clicks')
    @login_required
    def api_clicks():
        return jsonify(get_report_data())

    @app.route('/api/delete', methods=['POST'])
    @login_required
    def api_delete():
        ids = request.json.get('ids', [])
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute(
            f"DELETE FROM clicks WHERE id IN ({','.join('?' * len(ids))})",
            ids
        )
        conn.commit()
        conn.close()
        return {"status": "ok"}
