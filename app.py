import os
import sqlite3
from flask import Flask, redirect, request, render_template, send_file, jsonify
from io import BytesIO, StringIO
from datetime import datetime
import pandas as pd  # Для экспорта в Excel
import logging


BASE_DIR = os.path.dirname(os.path.abspath(__file__))   # Определяем базовую директорию, где находится текущий файл
DATABASE = os.path.join(BASE_DIR, 'phishing_data.db')   # Путь к базе данных SQLite
app = Flask(__name__, template_folder=BASE_DIR)         # Инициализация Flask-приложения


# -----------------------------
# Настройка логирования
# -----------------------------
class IgnoreApiClicksFilter(logging.Filter):
    """Фильтрует сообщения /api/clicks из логов werkzeug"""
    def filter(self, record):
        # Если строка содержит /api/clicks, игнорируем её
        return '/api/clicks' not in record.getMessage()

# Получаем логгер werkzeug (Flask использует его для запросов)
werkzeug_logger = logging.getLogger('werkzeug')
werkzeug_logger.addFilter(IgnoreApiClicksFilter())
# Уровень оставляем INFO, чтобы видеть ошибки и переходы
werkzeug_logger.setLevel(logging.INFO)


# -----------------------------
# DB init
# -----------------------------
def initialize_db():
    """Функция для инициализации базы данных, если она еще не существует"""
    if not os.path.exists(DATABASE):
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE clicks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                ip TEXT,
                user_agent TEXT,
                token TEXT
            )
        ''')
        conn.commit()
        conn.close()


# -----------------------------
# Чтение данных из базы
# -----------------------------
def get_report_data():
    """Извлечение данных из базы данных"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM clicks ORDER BY id DESC")
    data = cursor.fetchall()
    conn.close()

    # Преобразуем данные в список словарей
    return [
        {
            "id": row[0],
            "timestamp": row[1],
            "ip": row[2],
            "user_agent": row[3],
            "token": row[4]
        }
        for row in data
    ]


# -----------------------------
# Экспорт данных
# -----------------------------
@app.route('/export/excel')
def export_excel():
    """Экспорт данных в Excel файл"""
    data = get_report_data()
    if not data:
        return "Нет данных для экспорта", 400

    df = pd.DataFrame(data)

    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Phishing Report')

    buffer.seek(0)
    return send_file(
        buffer,
        as_attachment=True,
        download_name='phishing_report.xlsx',
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )


@app.route('/export/txt')
def export_txt():
    """Экспорт данных в текстовый файл (.txt)"""
    data = get_report_data()

    buffer = StringIO()
    for row in data:
        buffer.write(
            f"{row['timestamp']} | {row['ip']} | {row['user_agent']} | {row['token']}\n"
        )

    return send_file(
        BytesIO(buffer.getvalue().encode('utf-8')),
        as_attachment=True,
        download_name='phishing_report.txt',
        mimetype='text/plain'
    )


@app.route('/export/sql')
def export_sql():
    """Экспорт данных в SQL-формат (.sql)"""
    data = get_report_data()

    buffer = StringIO()
    buffer.write("""CREATE TABLE clicks (
timestamp TEXT,
ip TEXT,
user_agent TEXT,
token TEXT
);\n\n""")

    for row in data:
        buffer.write(
            f"INSERT INTO clicks VALUES "
            f"('{row['timestamp']}', '{row['ip']}', '{row['user_agent']}', '{row['token']}');\n"
        )

    return send_file(
        BytesIO(buffer.getvalue().encode('utf-8')),
        as_attachment=True,
        download_name='phishing_report.sql',
        mimetype='application/sql'
    )


@app.route('/export/db')
def export_db():
    """Экспорт данных в SQLite базу данных (.db)"""
    data = get_report_data()

    buffer = BytesIO()
    conn = sqlite3.connect(':memory:')
    cursor = conn.cursor()
    cursor.execute(
        '''CREATE TABLE clicks (timestamp TEXT, ip TEXT, user_agent TEXT, token TEXT)'''
    )

    for row in data:
        cursor.execute(
            "INSERT INTO clicks VALUES (?, ?, ?, ?)",
            (row['timestamp'], row['ip'], row['user_agent'], row['token'])
        )

    for line in conn.iterdump():
        buffer.write(f"{line}\n".encode())

    conn.close()
    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name='phishing_report.db',
        mimetype='application/octet-stream'
    )


# -----------------------------
# API для фронтенда
# -----------------------------
@app.route('/api/clicks')
def api_clicks():
    """Получение данных в формате JSON (для автообновления таблицы)"""
    return jsonify(get_report_data())


@app.route('/api/delete', methods=['POST'])
def api_delete():
    """Удаление выбранных записей по ID"""
    ids = request.json.get('ids', [])

    if not ids:
        return {"status": "no_ids"}, 400

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute(
        f"DELETE FROM clicks WHERE id IN ({','.join('?' for _ in ids)})",
        ids
    )
    conn.commit()
    conn.close()

    return {"status": "ok"}


# -----------------------------
# Логирование кликов
# -----------------------------
def log_click(ip, user_agent, token):
    """Запись клика в базу данных"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO clicks (timestamp, ip, user_agent, token) VALUES (?, ?, ?, ?)",
        (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), ip, user_agent, token)
    )
    conn.commit()
    conn.close()


# -----------------------------
# Панель управления
# -----------------------------
@app.route('/')
def dashboard():
    """Отображение панели с данными о переходах по фишинговым ссылкам"""
    return render_template('dashboard.html')


# -----------------------------
# Отслеживание фишинговых ссылок
# -----------------------------
@app.route('/track/<token>')
def track(token):
    """Логирование перехода по фишинговой ссылке"""
    ip = request.remote_addr
    user_agent = request.headers.get('User-Agent', 'unknown')

    log_click(ip, user_agent, token)
    return redirect('https://ya.ru')  # Рекомендуется локальный редирект


# -----------------------------
# Запуск приложения
# -----------------------------
if __name__ == '__main__':
    initialize_db()
    app.run(host='0.0.0.0', port=8080, debug=True)
