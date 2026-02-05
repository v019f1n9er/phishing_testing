import os
import sqlite3
import logging
import secrets
from flask import Flask, redirect, request, render_template, send_file, jsonify, session, url_for
from io import BytesIO, StringIO
from datetime import datetime, timedelta
import pandas as pd  # Для экспорта в Excel
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash

# -----------------------------
# Определяем базовую директорию и путь к БД
# -----------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, 'phishing_data.db')

# -----------------------------
# Инициализация Flask-приложения
# -----------------------------
app = Flask(__name__, template_folder=BASE_DIR)

# -----------------------------
# НАСТРОЙКИ СЕССИЙ И БЕЗОПАСНОСТИ
# -----------------------------
app.secret_key = 'phishing-dashboard-2026-super-secret-key'  # Ключ для шифрования сессий

# Таймаут неактивной сессии (автовыход)
IDLE_TIMEOUT_MINUTES = 15
app.permanent_session_lifetime = timedelta(minutes=IDLE_TIMEOUT_MINUTES)

# Настройки cookies
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    SESSION_COOKIE_SECURE=False  # True при HTTPS
)

# -----------------------------
# Настройка логирования
# -----------------------------
class IgnoreApiClicksFilter(logging.Filter):
    """Фильтрует сообщения /api/clicks из логов werkzeug"""
    def filter(self, record):
        return '/api/clicks' not in record.getMessage()

werkzeug_logger = logging.getLogger('werkzeug')
werkzeug_logger.addFilter(IgnoreApiClicksFilter())
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
# Таблица пользователей
# -----------------------------
def initialize_users():
    """Создание таблицы users и дефолтного администратора"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT
        )
    ''')

    # Если пользователей нет — создаем admin:passwd123
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        cursor.execute(
            "INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?)",
            (
                'admin',
                generate_password_hash('passwd123'),
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            )
        )

    conn.commit()
    conn.close()

# -----------------------------
# CSRF
# -----------------------------
def generate_csrf_token():
    """Генерируем CSRF токен и сохраняем в сессии"""
    if '_csrf_token' not in session:
        session['_csrf_token'] = secrets.token_hex(32)
    return session['_csrf_token']

app.jinja_env.globals['csrf_token'] = generate_csrf_token

@app.before_request
def csrf_protect():
    """Проверка CSRF токена при POST запросах"""
    if request.method == "POST":
        token = session.get('_csrf_token')
        form_token = request.form.get('_csrf_token') or request.headers.get('X-CSRF-Token')
        if not token or token != form_token:
            return "CSRF validation failed", 403

# -----------------------------
# Автовыход по неактивности
# -----------------------------
@app.before_request
def session_timeout_check():
    """Если пользователь авторизован, обновляем сессию, чтобы отслеживать активность"""
    if session.get('user_id'):
        session.permanent = True  # Используем timedelta из app.permanent_session_lifetime
        session.modified = True

# -----------------------------
# Декоратор авторизации
# -----------------------------
def login_required(f):
    """Обертка для маршрутов, требующих авторизации"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('user_id'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# -----------------------------
# Авторизация
# -----------------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    """Маршрут для логина"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, password_hash FROM users WHERE username = ?",
            (username,)
        )
        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user[1], password):
            session.clear()
            session['user_id'] = user[0]
            session['username'] = username
            return redirect(url_for('dashboard'))

        return render_template('login.html', error='Неверный логин или пароль')

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    """Выход из аккаунта"""
    session.clear()
    return redirect(url_for('login'))

# -----------------------------
# Чтение данных из базы
# -----------------------------
def get_report_data():
    """Получаем все клики из БД"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM clicks ORDER BY id DESC")
    data = cursor.fetchall()
    conn.close()

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
@login_required
def export_excel():
    """Экспорт в Excel"""
    df = pd.DataFrame(get_report_data())
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name='phishing_report.xlsx')

@app.route('/export/txt')
@login_required
def export_txt():
    """Экспорт в TXT"""
    buffer = StringIO()
    for row in get_report_data():
        buffer.write(f"{row['timestamp']} | {row['ip']} | {row['user_agent']} | {row['token']}\n")
    return send_file(BytesIO(buffer.getvalue().encode()), as_attachment=True, download_name='phishing_report.txt')

@app.route('/export/sql')
@login_required
def export_sql():
    """Экспорт в SQL"""
    buffer = StringIO()
    buffer.write("CREATE TABLE clicks (timestamp TEXT, ip TEXT, user_agent TEXT, token TEXT);\n\n")
    for row in get_report_data():
        buffer.write(
            f"INSERT INTO clicks VALUES ('{row['timestamp']}', '{row['ip']}', '{row['user_agent']}', '{row['token']}');\n"
        )
    return send_file(BytesIO(buffer.getvalue().encode()), as_attachment=True, download_name='phishing_report.sql')

@app.route('/export/db')
@login_required
def export_db():
    """Экспорт базы SQLite"""
    buffer = BytesIO()
    conn = sqlite3.connect(':memory:')
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE clicks (timestamp TEXT, ip TEXT, user_agent TEXT, token TEXT)")
    for row in get_report_data():
        cursor.execute("INSERT INTO clicks VALUES (?, ?, ?, ?)",
                       (row['timestamp'], row['ip'], row['user_agent'], row['token']))
    for line in conn.iterdump():
        buffer.write(f"{line}\n".encode())
    conn.close()
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name='phishing_report.db')

# -----------------------------
# API
# -----------------------------
@app.route('/api/clicks')
@login_required
def api_clicks():
    """Возвращает все клики в JSON"""
    return jsonify(get_report_data())

@app.route('/api/delete', methods=['POST'])
@login_required
def api_delete():
    """Удаление выбранных записей"""
    ids = request.json.get('ids', [])
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute(f"DELETE FROM clicks WHERE id IN ({','.join('?' for _ in ids)})", ids)
    conn.commit()
    conn.close()
    return {"status": "ok"}

# -----------------------------
# Панель управления
# -----------------------------
@app.route('/')
@login_required
def dashboard():
    """Главная страница dashboard"""
    return render_template('dashboard.html')

# -----------------------------
# Трекинг (ПУБЛИЧНЫЙ)
# -----------------------------
@app.route('/track/<token>')
def track(token):
    """Публичный маршрут для трекинга кликов по токену"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO clicks (timestamp, ip, user_agent, token) VALUES (?, ?, ?, ?)",
        (datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
         request.remote_addr,
         request.headers.get('User-Agent', 'unknown'),
         token)
    )
    conn.commit()
    conn.close()
    return redirect('https://ya.ru')

# -----------------------------
# Запуск
# -----------------------------
if __name__ == '__main__':
    initialize_db()
    initialize_users()
    app.run(host='0.0.0.0', port=8080, debug=False, use_reloader=False)
