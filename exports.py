from flask import send_file
from io import BytesIO, StringIO
import sqlite3
import pandas as pd

from security import login_required
from api import get_report_data
from config import DATABASE

def register_export_routes(app):

    @app.route('/export/excel')
    @login_required
    def export_excel():
        df = pd.DataFrame(get_report_data())
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df.to_excel(writer, index=False)
        buffer.seek(0)
        return send_file(
            buffer,
            as_attachment=True,
            download_name='phishing_report.xlsx'
        )

    @app.route('/export/txt')
    @login_required
    def export_txt():
        buffer = StringIO()
        for row in get_report_data():
            buffer.write(
                f"{row['timestamp']} | {row['ip']} | "
                f"{row['user_agent']} | {row['token']}\n"
            )
        return send_file(
            BytesIO(buffer.getvalue().encode()),
            as_attachment=True,
            download_name='phishing_report.txt'
        )

    @app.route('/export/sql')
    @login_required
    def export_sql():
        buffer = StringIO()
        buffer.write(
            "CREATE TABLE clicks "
            "(timestamp TEXT, ip TEXT, user_agent TEXT, token TEXT);\n\n"
        )
        for row in get_report_data():
            buffer.write(
                "INSERT INTO clicks VALUES "
                f"('{row['timestamp']}', '{row['ip']}', "
                f"'{row['user_agent']}', '{row['token']}');\n"
            )
        return send_file(
            BytesIO(buffer.getvalue().encode()),
            as_attachment=True,
            download_name='phishing_report.sql'
        )

    @app.route('/export/db')
    @login_required
    def export_db():
        buffer = BytesIO()
        conn = sqlite3.connect(':memory:')
        cursor = conn.cursor()

        cursor.execute(
            "CREATE TABLE clicks "
            "(timestamp TEXT, ip TEXT, user_agent TEXT, token TEXT)"
        )

        for row in get_report_data():
            cursor.execute(
                "INSERT INTO clicks VALUES (?, ?, ?, ?)",
                (
                    row['timestamp'],
                    row['ip'],
                    row['user_agent'],
                    row['token']
                )
            )

        for line in conn.iterdump():
            buffer.write(f"{line}\n".encode())

        conn.close()
        buffer.seek(0)

        return send_file(
            buffer,
            as_attachment=True,
            download_name='phishing_report.db'
        )
