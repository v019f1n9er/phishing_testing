import os
import sqlite3
from flask import Flask, redirect, request, render_template, send_file
from io import BytesIO, StringIO
from datetime import datetime
import pandas as pd  # Для экспорта в Excel

# Определяем базовую директорию, где находится текущий файл
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Инициализация Flask-приложения
app = Flask(__name__, template_folder=BASE_DIR)

# Путь к базе данных SQLite
DATABASE = os.path.join(BASE_DIR, 'phishing_data.db')


# -----------------------------
# DB init
# -----------------------------
def initialize_db():
    """Функция для инициализации базы данных, если она еще не существует"""
    if not os.path.exists(DATABASE):  # Если база данных не существует
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE clicks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            ip TEXT,
            user_agent TEXT,
            token TEXT
        )''')
        conn.commit()
        conn.close()


# -----------------------------
# Чтение данных из базы
# -----------------------------
def get_report_data():
    """Извлечение данных из базы данных"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM clicks")  # Извлекаем все данные
    data = cursor.fetchall()
    conn.close()

    # Преобразуем данные в список словарей
    return [
        {"id": row[0], "timestamp": row[1], "ip": row[2], "user_agent": row[3], "token": row[4]}
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
        return "Нет данных для экспорта", 400  # Если нет данных

    # Создаем DataFrame
    df = pd.DataFrame(data)

    # Экспортируем в Excel
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Phishing Report')

    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name='phishing_report.xlsx', mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


@app.route('/export/txt')
def export_txt():
    """Экспорт данных в текстовый файл (.txt)"""
    data = get_report_data()

    buffer = StringIO()
    for row in data:
        buffer.write(f"{row['timestamp']} | {row['ip']} | {row['user_agent']} | {row['token']}\n")

    return send_file(BytesIO(buffer.getvalue().encode('utf-8')), as_attachment=True, download_name='phishing_report.txt', mimetype='text/plain')


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
        buffer.write(f"INSERT INTO clicks VALUES ('{row['timestamp']}', '{row['ip']}', '{row['user_agent']}', '{row['token']}');\n")

    return send_file(BytesIO(buffer.getvalue().encode('utf-8')), as_attachment=True, download_name='phishing_report.sql', mimetype='application/sql')


@app.route('/export/db')
def export_db():
    """Экспорт данных в SQLite базу данных (.db)"""
    data = get_report_data()

    buffer = BytesIO()
    conn = sqlite3.connect(':memory:')  # Временная база данных в памяти
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE clicks (timestamp TEXT, ip TEXT, user_agent TEXT, token TEXT)''')

    for row in data:
        cursor.execute("INSERT INTO clicks (timestamp, ip, user_agent, token) VALUES (?, ?, ?, ?)",
                       (row['timestamp'], row['ip'], row['user_agent'], row['token']))

    # Экспорт в строковый формат
    for line in conn.iterdump():
        buffer.write(f"{line}\n".encode())

    conn.close()
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name='phishing_report.db', mimetype='application/octet-stream')


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
    data = get_report_data()
    return render_template('dashboard.html', data=data)


# -----------------------------
# Отслеживание фишинговых ссылок
# -----------------------------
@app.route('/track/<token>')
def track(token):
    """Логирование перехода по фишинговой ссылке"""
    ip = request.remote_addr  # IP-адрес пользователя
    user_agent = request.headers.get('User-Agent', 'unknown')  # User-Agent браузера

    log_click(ip, user_agent, token)  # Логируем данные о клике
    return redirect('https://ya.ru')  # Перенаправление на сайт


# Запуск приложения
if __name__ == '__main__':
    initialize_db()  # Инициализация базы данных
    app.run(host='0.0.0.0', port=8080, debug=True)  # Запуск сервера Flask
