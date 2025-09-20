import os
from flask import Flask, redirect, request
import pandas as pd
from datetime import datetime

app = Flask(__name__)

# Путь к Excel-файлу
EXCEL_FILE = 'phishing_data.xlsx'

# Удаляем файл, если он поврежден
def reset_excel_file():
    if os.path.exists(EXCEL_FILE):
        try:
            # Попытка открыть файл как Excel
            df = pd.read_excel(EXCEL_FILE, engine='openpyxl')
        except Exception as e:
            print(f"Ошибка при открытии файла: {e}. Удаляем файл и создаем новый.")
            os.remove(EXCEL_FILE)

# Инициализация файла Excel, если он не существует
def initialize_excel():
    reset_excel_file()  # Удаляем поврежденный файл, если он существует
    if not os.path.exists(EXCEL_FILE):
        try:
            # Создаем новый DataFrame с нужными столбцами
            df = pd.DataFrame(columns=["Timestamp", "IP Address"])
            df.to_excel(EXCEL_FILE, index=False, engine='openpyxl')
            print("Новый Excel файл создан.")
        except Exception as e:
            print(f"Ошибка при создании Excel файла: {e}")

# Функция для записи данных о переходе
def log_redirect(ip_address):
    try:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Чтение и добавление данных в Excel
        df = pd.read_excel(EXCEL_FILE, engine='openpyxl')
        
        # Создаем новый DataFrame с одной строкой данных
        new_data = pd.DataFrame({"Timestamp": [timestamp], "IP Address": [ip_address]})
        
        # Используем pd.concat для добавления новых данных в DataFrame
        df = pd.concat([df, new_data], ignore_index=True)
        
        # Сохраняем измененный DataFrame обратно в Excel
        df.to_excel(EXCEL_FILE, index=False, engine='openpyxl')
        print(f"Логирование IP: {ip_address} успешно!")
    except Exception as e:
        print(f"Ошибка при записи в Excel: {e}")

# Редирект на реальный сайт
@app.route('/')
def phishing_redirect():
    try:
        ip_address = request.remote_addr  # Получаем IP-адрес
        log_redirect(ip_address)  # Логируем информацию

        # Редирект на любой реальный сайт, например, Google
        return redirect("https://www.google.com")
    except Exception as e:
        print(f"Ошибка при обработке запроса: {e}")
        return "Произошла ошибка на сервере. Пожалуйста, попробуйте позже.", 500

if __name__ == '__main__':
    try:
        initialize_excel()  # Инициализация файла
        app.run(host='0.0.0.0', port=8080)
    except Exception as e:
        print(f"Ошибка при запуске сервера: {e}")
