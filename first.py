import os  # модуль для работы с файловой системой (пути, проверка существования файлов)
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
