import sqlite3
from flask import jsonify, request
from config import DATABASE
from security import login_required
from click_analytics import ClickAnalytics
from datetime import datetime

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

def get_click_analytics_data():
    """Получить аналитику кликов из базы данных"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # Получаем общее количество уникальных ссылок (email токены)
    cursor.execute("SELECT COUNT(DISTINCT token) FROM emails")
    total_links = cursor.fetchone()[0]
    
    # Получаем общее количество кликов
    cursor.execute("SELECT COUNT(*) FROM clicks")
    total_clicks = cursor.fetchone()[0]
    
    # Получаем количество ссылок (email_id), по которым был хотя бы один клик
    cursor.execute("SELECT COUNT(DISTINCT email_id) FROM clicks WHERE email_id IS NOT NULL")
    unique_clicked_links = cursor.fetchone()[0]
    
    conn.close()
    
    # Используем класс ClickAnalytics для анализа
    analytics = ClickAnalytics({
        'total_links': total_links,
        'total_clicks': total_clicks,
        'unique_clicked_links': unique_clicked_links
    })
    
    return analytics.get_analytics_report()

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

    @app.route('/api/analytics')
    @login_required
    def api_analytics():
        """API endpoint для получения аналитики кликов"""
        analytics_data = get_click_analytics_data()
        return jsonify(analytics_data)


def get_analytics_export_data():
    """Получить данные аналитики для экспорта"""
    analytics_data = get_click_analytics_data()
    
    return {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'total_links': analytics_data['total_links'],
        'total_clicks': analytics_data['total_clicks'],
        'unique_clicked_links': analytics_data['unique_clicked_links'],
        'non_clicked': analytics_data['non_clicked'],
        'click_ratio': analytics_data['click_ratio'],
        'click_percentage': analytics_data['click_percentage']
    }
