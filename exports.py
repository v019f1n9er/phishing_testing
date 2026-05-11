from flask import send_file
from io import BytesIO, StringIO
import sqlite3
import pandas as pd
import json

from security import login_required
from api import get_report_data, get_analytics_export_data
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

    @app.route('/export/analytics_excel')
    @login_required
    def export_analytics_excel():
        data = get_analytics_export_data()
        df = pd.DataFrame([data])
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Аналитика')
        buffer.seek(0)
        return send_file(
            buffer,
            as_attachment=True,
            download_name='analytics_report.xlsx'
        )

    @app.route('/export/analytics_txt')
    @login_required
    def export_analytics_txt():
        data = get_analytics_export_data()
        buffer = StringIO()
        buffer.write("=" * 60 + "\n")
        buffer.write("ОТЧЕТ АНАЛИТИКИ КЛИКОВ\n")
        buffer.write("=" * 60 + "\n\n")
        buffer.write(f"Дата создания отчета: {data['timestamp']}\n\n")
        buffer.write(f"Всего ссылок в кампании: {data['total_links']}\n")
        buffer.write(f"Всего кликов: {data['total_clicks']}\n")
        buffer.write(f"Количество ссылок с кликами: {data['unique_clicked_links']}\n")
        buffer.write(f"Количество ссылок без кликов: {data['non_clicked']}\n")
        buffer.write(f"Соотношение клики/ссылки: {data['click_ratio']}\n")
        buffer.write(f"Процент ссылок с кликами: {data['click_percentage']}%\n")
        buffer.write("\n" + "=" * 60 + "\n")
        
        return send_file(
            BytesIO(buffer.getvalue().encode()),
            as_attachment=True,
            download_name='analytics_report.txt'
        )

    @app.route('/export/analytics_json')
    @login_required
    def export_analytics_json():
        data = get_analytics_export_data()
        json_data = json.dumps(data, ensure_ascii=False, indent=2)
        return send_file(
            BytesIO(json_data.encode()),
            as_attachment=True,
            download_name='analytics_report.json',
            mimetype='application/json'
        )

    @app.route('/export/analytics_html')
    @login_required
    def export_analytics_html():
        data = get_analytics_export_data()
        
        # Рассчитываем процент не открытых ссылок
        not_clicked_percentage = 100 - data['click_percentage']
        
        html_content = f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Отчет анализа кликов</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@3.9.1/dist/chart.min.js"></script>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            margin: 0;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 10px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            padding: 40px;
        }}
        
        h1 {{
            color: #333;
            text-align: center;
            margin-bottom: 10px;
            font-size: 32px;
        }}
        
        .timestamp {{
            text-align: center;
            color: #999;
            font-size: 14px;
            margin-bottom: 40px;
        }}
        
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }}
        
        .metric-card {{
            background: linear-gradient(135deg, #28a745 0%, #20c997 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            text-align: center;
        }}
        
        .metric-card-red {{
            background: linear-gradient(135deg, #dc3545 0%, #c82333 100%) !important;
        }}
        
        .metric-value {{
            font-size: 48px;
            font-weight: bold;
            margin: 10px 0;
        }}
        
        .metric-label {{
            font-size: 14px;
            opacity: 0.9;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        
        .charts-section {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 40px;
            margin-bottom: 40px;
            align-items: center;
        }}
        
        .chart-container {{
            position: relative;
            height: 300px;
            background: white;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        
        .chart-title {{
            text-align: center;
            color: #333;
            margin-bottom: 20px;
            font-weight: bold;
        }}
        
        .stats-table {{
            width: 100%;
            border-collapse: collapse;
            background: white;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            margin-top: 40px;
        }}
        
        .stats-table th {{
            background: #28a745;
            color: white;
            padding: 15px;
            text-align: left;
            font-weight: bold;
        }}
        
        .stats-table td {{
            padding: 15px;
            border-bottom: 1px solid #eee;
        }}
        
        .stats-table tr:hover {{
            background: #f5f5f5;
        }}
        
        .stats-table tr:last-child td {{
            border-bottom: none;
        }}
        
        .stat-label {{
            color: #333;
            font-weight: 500;
        }}
        
        .stat-value {{
            color: #28a745;
            font-weight: bold;
            font-size: 16px;
        }}
        
        @media (max-width: 768px) {{
            .container {{
                padding: 20px;
            }}
            
            h1 {{
                font-size: 24px;
            }}
            
            .charts-section {{
                grid-template-columns: 1fr;
            }}
            
            .metrics-grid {{
                grid-template-columns: 1fr;
            }}
        }}
        
        .footer {{
            text-align: center;
            color: #999;
            font-size: 12px;
            margin-top: 40px;
            border-top: 1px solid #eee;
            padding-top: 20px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Отчет аналитики кликов</h1>
        <div class="timestamp">Дата создания: {data['timestamp']}</div>
        
        <!-- Metric Cards -->
        <div class="metrics-grid">
            <div class="metric-card">
                <div class="metric-label">Всего ссылок</div>
                <div class="metric-value">{data['total_links']}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Всего кликов</div>
                <div class="metric-value">{data['total_clicks']}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Ссылок с кликами</div>
                <div class="metric-value">{data['unique_clicked_links']}</div>
            </div>
            <div class="metric-card metric-card-red">
                <div class="metric-label">Процент переходов по ссылкам</div>
                <div class="metric-value">{data['click_percentage']:.2f}%</div>
            </div>
        </div>
        
        <!-- Charts -->
        <div class="charts-section">
            <div class="chart-container">
                <div class="chart-title">Распределение кликов</div>
                <canvas id="clicksChart"></canvas>
            </div>
            <div class="chart-container">
                <div class="chart-title">Статус ссылок</div>
                <canvas id="statusChart"></canvas>
            </div>
        </div>
        
        <!-- Statistics Table -->
        <table class="stats-table">
            <thead>
                <tr>
                    <th>Метрика</th>
                    <th>Значение</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td class="stat-label">Общее количество ссылок в кампании</td>
                    <td class="stat-value">{data['total_links']}</td>
                </tr>
                <tr>
                    <td class="stat-label">Количество кликов</td>
                    <td class="stat-value">{data['total_clicks']}</td>
                </tr>
                <tr>
                    <td class="stat-label">Ссылок с хотя бы одним кликом</td>
                    <td class="stat-value">{data['unique_clicked_links']}</td>
                </tr>
                <tr>
                    <td class="stat-label">Ссылок без кликов</td>
                    <td class="stat-value">{data['non_clicked']}</td>
                </tr>
                <tr>
                    <td class="stat-label">Соотношение клики/ссылки</td>
                    <td class="stat-value">{data['click_ratio']:.2f}</td>
                </tr>
                <tr>
                    <td class="stat-label">Процент переходов по ссылкам</td>
                    <td class="stat-value">{data['click_percentage']:.2f}%</td>
                </tr>
            </tbody>
        </table>
        
        <div class="footer">
            <p>Отчет автоматически сгенерирован системой анализа кликов</p>
        </div>
    </div>
    
    <script>
        // Pie Chart - Click Distribution
        const clicksCtx = document.getElementById('clicksChart').getContext('2d');
        new Chart(clicksCtx, {{
            type: 'doughnut',
            data: {{
                labels: ['Ссылки с кликами', 'Ссылки без кликов'],
                datasets: [{{
                    data: [{data['unique_clicked_links']}, {data['non_clicked']}],
                    backgroundColor: [
                        'rgba(40, 167, 69, 0.8)',
                        'rgba(220, 53, 69, 0.8)'
                    ],
                    borderColor: [
                        'rgba(40, 167, 69, 1)',
                        'rgba(220, 53, 69, 1)'
                    ],
                    borderWidth: 2
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{
                        position: 'bottom'
                    }}
                }}
            }}
        }});
        
        // Bar Chart - Clicks Statistics
        const statusCtx = document.getElementById('statusChart').getContext('2d');
        new Chart(statusCtx, {{
            type: 'bar',
            data: {{
                labels: ['Ссылки с кликами', 'Ссылки без кликов'],
                datasets: [{{
                    label: 'Количество ссылок',
                    data: [{data['unique_clicked_links']}, {data['non_clicked']}],
                    backgroundColor: [
                        'rgba(40, 167, 69, 0.7)',
                        'rgba(220, 53, 69, 0.7)'
                    ],
                    borderColor: [
                        'rgba(40, 167, 69, 1)',
                        'rgba(220, 53, 69, 1)'
                    ],
                    borderWidth: 2
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                indexAxis: 'y',
                plugins: {{
                    legend: {{
                        display: false
                    }}
                }},
                scales: {{
                    x: {{
                        beginAtZero: true
                    }}
                }}
            }}
        }});
    </script>
</body>
</html>"""
        
        return send_file(
            BytesIO(html_content.encode('utf-8')),
            as_attachment=True,
            download_name='analytics_report.html',
            mimetype='text/html'
        )
