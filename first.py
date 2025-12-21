import os  # модуль для работы с файловой системой (пути, проверка существования файлов)
import sqlite3
from flask import send_file
from io import BytesIO, StringIO
from flask import Flask, redirect, request, render_template  # Flask для веб-сервиса, render_template для HTML-шаблонов
import pandas as pd  # pandas для работы с Excel (чтение, запись, таблицы)
from datetime import datetime  # datetime для получения текущей даты и времени

# Определяем базовую директорию, где находится текущий файл
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Инициализация Flask-приложения, указываем директорию шаблонов как BASE_DIR
app = Flask(__name__, template_folder=BASE_DIR)

# Полный путь к Excel-файлу, где будут храниться логи
EXCEL_FILE = os.path.join(BASE_DIR, 'phishing_data.xlsx')


# -----------------------------
# Excel init
# -----------------------------
# Функция для создания Excel-файла, если его ещё нет
def initialize_excel():
    if not os.path.exists(EXCEL_FILE):  # проверяем, существует ли файл
        # Создаём пустой DataFrame с нужными столбцами
        df = pd.DataFrame(columns=[
            "Timestamp",  # время клика
            "IP Address",  # IP пользователя
            "User-Agent",  # браузер / устройство
            "Token"       # уникальный идентификатор фишинговой ссылки
        ])
        # Сохраняем DataFrame в Excel
        df.to_excel(EXCEL_FILE, index=False, engine='openpyxl')


# Универсальная функция чтения данных
def get_report_df():
    return pd.read_excel(EXCEL_FILE, engine='openpyxl')
@app.route('/export/excel')
def export_excel():
    df = get_report_df()

    buffer = BytesIO()
    df.to_excel(buffer, index=False, engine='openpyxl')
    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name='phishing_report.xlsx',
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
@app.route('/export/txt')
def export_txt():
    df = get_report_df()

    buffer = StringIO()
    for _, row in df.iterrows():
        buffer.write(
            f"{row['Timestamp']} | {row['IP Address']} | "
            f"{row['User-Agent']} | {row['Token']}\n"
        )

    return send_file(
        BytesIO(buffer.getvalue().encode('utf-8')),
        as_attachment=True,
        download_name='phishing_report.txt',
        mimetype='text/plain'
    )
@app.route('/export/sql')
def export_sql():
    df = get_report_df()

    buffer = StringIO()
    buffer.write("""CREATE TABLE clicks (
        timestamp TEXT,
        ip TEXT,
        user_agent TEXT,
        token TEXT
    );\n\n""")

    for _, row in df.iterrows():
        buffer.write(
            "INSERT INTO clicks VALUES "
            f"('{row['Timestamp']}', '{row['IP Address']}', "
            f"'{row['User-Agent']}', '{row['Token']}');\n"
        )

    return send_file(
        BytesIO(buffer.getvalue().encode('utf-8')),
        as_attachment=True,
        download_name='phishing_report.sql',
        mimetype='application/sql'
    )
@app.route('/export/db')
def export_db():
    df = get_report_df()

    buffer = BytesIO()
    conn = sqlite3.connect(':memory:')
    df.to_sql('clicks', conn, index=False, if_exists='replace')

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
# Log click
# -----------------------------
# Функция для записи клика по фишинговой ссылке в Excel
def log_click(ip, user_agent, token):
    # Читаем текущий Excel-файл
    df = pd.read_excel(EXCEL_FILE, engine='openpyxl')

    # Добавляем новую строку с информацией о клике
    df.loc[len(df)] = [
        datetime.now().strftime('%Y-%m-%d %H:%M:%S'),  # текущее время в формате ГГГГ-ММ-ДД ЧЧ:ММ:СС
        ip,  # IP пользователя
        user_agent,  # User-Agent
        token  # идентификатор ссылки
    ]

    # Сохраняем обновленный DataFrame обратно в Excel
    df.to_excel(EXCEL_FILE, index=False, engine='openpyxl')


# -----------------------------
# Admin dashboard
# -----------------------------
# Маршрут для главной страницы с панелью администратора
@app.route('/')
def dashboard():
    # Читаем все данные из Excel
    df = pd.read_excel(EXCEL_FILE, engine='openpyxl')
    # Преобразуем данные в список словарей для Jinja-шаблона
    data = df.to_dict(orient='records')
    # Вывод в консоль для отладки, сколько строк рендерится
    print("Rendering template with", len(data), "rows")
    # Отправляем HTML-шаблон на рендеринг вместе с данными
    return render_template('dashboard.html', data=data)


# -----------------------------
# Phishing link
# -----------------------------
# Маршрут для отслеживания перехода по фишинговой ссылке
@app.route('/track/<token>')
def track(token):
    # Выводим в консоль токен для отладки
    print("CLICK:", token)
    # Выводим IP пользователя
    print("IP:", request.remote_addr)

    # Получаем IP пользователя
    ip = request.remote_addr
    # Получаем User-Agent браузера (или 'unknown', если его нет)
    user_agent = request.headers.get('User-Agent', 'unknown')

    # Логируем клик в Excel
    log_click(ip, user_agent, token)

    # Редирект на реальный сайт (https://ya.ru)
    return redirect('https://ya.ru')


# Если файл запускается напрямую
if __name__ == '__main__':
    initialize_excel()  # Инициализация Excel (создание при отсутствии)
    app.run(host='0.0.0.0', port=8080, debug=True)  # Запуск Flask-сервера на всех интерфейсах, порт 8080, debug-режим
