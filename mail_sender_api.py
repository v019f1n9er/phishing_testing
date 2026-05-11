"""
API endpoints для управления отправкой писем и уведомлениями
"""

from flask import request, jsonify
from security import login_required
from mail_sender import init_mail_sending_tables
from mail_scheduler import scheduler
from mail_notifications import notification_manager
from datetime import datetime, timedelta
import logging
import json
import sqlite3
from config import DATABASE

logger = logging.getLogger(__name__)


def _init_template_tables():
    """Инициализировать таблицы для сохранения шаблонов"""
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS mail_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                subject TEXT NOT NULL,
                body TEXT NOT NULL,
                html TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()
        logger.info("Таблица mail_templates инициализирована")
    except Exception as e:
        logger.error(f"Ошибка при инициализации таблицы шаблонов: {e}")


def register_mail_sender_routes(app):
    """Регистрировать маршруты для отправки писем"""
    
    # Инициализируем таблицы при запуске
    init_mail_sending_tables()
    _init_template_tables()
    
    @app.route('/mail-sender')
    @login_required
    def mail_sender_page():
        """Страница отправки писем"""
        from flask import render_template
        return render_template('mail_sender.html')
    
    @app.route('/api/mail-sender/create-campaign', methods=['POST'])
    @login_required
    def create_campaign():
        """Создать кампанию отправки"""
        try:
            data = request.get_json()
            
            name = data.get('name', '').strip()
            from_account_id = data.get('from_account_id')
            subject = data.get('subject', '').strip()
            body = data.get('body', '').strip()
            html = data.get('html')
            recipients_text = data.get('recipients', '')
            
            # Валидация
            if not all([name, from_account_id, subject, body]):
                return jsonify({
                    'success': False,
                    'error': 'Не все обязательные поля заполнены'
                }), 400
            
            # Парсим получателей
            recipients = []
            for line in recipients_text.split('\n'):
                email = line.strip()
                if email and '@' in email:
                    recipients.append(email)
            
            if not recipients:
                return jsonify({
                    'success': False,
                    'error': 'Не найдено ни одного корректного email адреса'
                }), 400
            
            # Создаем кампанию
            campaign_id = scheduler.create_campaign(
                name=name,
                from_account_id=from_account_id,
                subject=subject,
                body=body,
                recipients=recipients,
                html=html
            )
            
            if campaign_id:
                return jsonify({
                    'success': True,
                    'message': f'Кампания "{name}" создана',
                    'campaign_id': campaign_id,
                    'recipient_count': len(recipients)
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'Ошибка при создании кампании'
                }), 500
        
        except Exception as e:
            logger.error(f"Ошибка при создании кампании: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/api/mail-sender/schedule-emails', methods=['POST'])
    @login_required
    def schedule_emails():
        """Планировать отправку писем"""
        try:
            data = request.get_json()
            
            campaign_id = data.get('campaign_id')
            start_date = datetime.fromisoformat(data.get('start_date'))
            end_date = datetime.fromisoformat(data.get('end_date'))
            random_schedule = data.get('random_schedule', True)
            require_confirmation = data.get('require_confirmation', False)
            
            if not campaign_id or not start_date or not end_date:
                return jsonify({
                    'success': False,
                    'error': 'Не все параметры указаны'
                }), 400
            
            if start_date >= end_date:
                return jsonify({
                    'success': False,
                    'error': 'Начальная дата должна быть раньше конечной'
                }), 400
            
            result = scheduler.schedule_emails(
                campaign_id=campaign_id,
                start_date=start_date,
                end_date=end_date,
                random_schedule=random_schedule,
                require_confirmation=require_confirmation
            )
            
            if result['success']:
                return jsonify(result)
            else:
                return jsonify(result), 400
        
        except Exception as e:
            logger.error(f"Ошибка при планировании: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/api/mail-sender/campaign-schedule/<int:campaign_id>', methods=['GET'])
    @login_required
    def get_campaign_schedule(campaign_id):
        """Получить превью расписания кампании"""
        try:
            limit = request.args.get('limit', 50, type=int)
            schedule = scheduler.get_campaign_schedule_preview(campaign_id, limit=limit)
            
            return jsonify({
                'success': True,
                'campaign_id': campaign_id,
                'schedule': schedule
            })
        
        except Exception as e:
            logger.error(f"Ошибка при получении расписания: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/api/mail-sender/confirm-campaign/<int:campaign_id>', methods=['POST'])
    @login_required
    def confirm_campaign(campaign_id):
        """Подтвердить кампанию"""
        try:
            if scheduler.confirm_campaign(campaign_id):
                return jsonify({
                    'success': True,
                    'message': 'Кампания подтверждена'
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'Ошибка при подтверждении'
                }), 500
        
        except Exception as e:
            logger.error(f"Ошибка при подтверждении: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/api/mail-sender/start-campaign/<int:campaign_id>', methods=['POST'])
    @login_required
    def start_campaign(campaign_id):
        """Запустить отправку кампании"""
        try:
            if scheduler.start_campaign(campaign_id):
                return jsonify({
                    'success': True,
                    'message': 'Кампания запущена',
                    'campaign_id': campaign_id
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'Ошибка при запуске кампании'
                }), 500
        
        except Exception as e:
            logger.error(f"Ошибка при запуске кампании: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/api/mail-sender/campaign-status/<int:campaign_id>', methods=['GET'])
    @login_required
    def get_campaign_status(campaign_id):
        """Получить статус кампании"""
        try:
            status = scheduler.get_campaign_status(campaign_id)
            
            if status:
                return jsonify({
                    'success': True,
                    'campaign': status
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'Кампания не найдена'
                }), 404
        
        except Exception as e:
            logger.error(f"Ошибка при получении статуса: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/api/mail-sender/cancel-campaign/<int:campaign_id>', methods=['POST'])
    @login_required
    def cancel_campaign(campaign_id):
        """Отменить кампанию"""
        try:
            if scheduler.cancel_campaign(campaign_id):
                return jsonify({
                    'success': True,
                    'message': 'Кампания отменена'
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'Ошибка при отмене'
                }), 500
        
        except Exception as e:
            logger.error(f"Ошибка при отмене: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    # ========== Endpoints для уведомлений ==========
    
    @app.route('/api/mail-notifications/list', methods=['GET'])
    @login_required
    def get_notifications_list():
        """Получить список уведомлений"""
        try:
            campaign_id = request.args.get('campaign_id', type=int)
            limit = request.args.get('limit', 100, type=int)
            offset = request.args.get('offset', 0, type=int)
            status = request.args.get('status')
            
            notifications = notification_manager.get_notifications(
                campaign_id=campaign_id,
                limit=limit,
                offset=offset,
                status_filter=status
            )
            
            return jsonify({
                'success': True,
                'notifications': notifications,
                'count': len(notifications)
            })
        
        except Exception as e:
            logger.error(f"Ошибка при получении уведомлений: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/api/mail-notifications/summary/<int:campaign_id>', methods=['GET'])
    @login_required
    def get_notifications_summary(campaign_id):
        """Получить сводку уведомлений"""
        try:
            summary = notification_manager.get_campaign_notifications_summary(campaign_id)
            
            return jsonify({
                'success': True,
                'campaign_id': campaign_id,
                'summary': summary
            })
        
        except Exception as e:
            logger.error(f"Ошибка при получении сводки: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/api/mail-notifications/export/<int:campaign_id>', methods=['GET'])
    @login_required
    def export_notifications(campaign_id):
        """Экспортировать уведомления"""
        try:
            format_type = request.args.get('format', 'json')
            
            if format_type not in ['json', 'csv', 'txt']:
                return jsonify({
                    'success': False,
                    'error': 'Неподдерживаемый формат'
                }), 400
            
            data = notification_manager.export_notifications(campaign_id, format=format_type)
            
            if data:
                return jsonify({
                    'success': True,
                    'format': format_type,
                    'data': data
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'Ошибка при экспорте'
                }), 500
        
        except Exception as e:
            logger.error(f"Ошибка при экспорте: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/api/mail-notifications/stats/<int:campaign_id>', methods=['GET'])
    @login_required
    def get_notification_stats(campaign_id):
        """Получить статистику по часам"""
        try:
            stats = notification_manager.get_notification_stats_by_hour(campaign_id)
            
            return jsonify({
                'success': True,
                'campaign_id': campaign_id,
                'stats': stats
            })
        
        except Exception as e:
            logger.error(f"Ошибка при получении статистики: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/api/mail-notifications/recent', methods=['GET'])
    @login_required
    def get_recent_notifications():
        """Получить последние уведомления"""
        try:
            limit = request.args.get('limit', 20, type=int)
            notifications = notification_manager.get_recent_notifications(limit=limit)
            
            return jsonify({
                'success': True,
                'notifications': notifications
            })
        
        except Exception as e:
            logger.error(f"Ошибка при получении уведомлений: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    # ========== Endpoints для шаблонов и получателей ==========
    
    @app.route('/api/mail-sender/recipients-list', methods=['GET'])
    @login_required
    def get_recipients_list():
        """Получить список всех email адресов из раздела Email адреса"""
        try:
            import sqlite3
            from config import DATABASE
            
            conn = sqlite3.connect(DATABASE)
            cursor = conn.cursor()
            cursor.execute("SELECT email FROM emails ORDER BY email ASC")
            rows = cursor.fetchall()
            conn.close()
            
            emails = [row[0] for row in rows]
            
            return jsonify({
                'success': True,
                'recipients': emails,
                'count': len(emails)
            })
        
        except Exception as e:
            logger.error(f"Ошибка при получении получателей: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/api/mail-sender/save-template', methods=['POST'])
    @login_required
    def save_template():
        """Сохранить шаблон письма"""
        try:
            import sqlite3
            from config import DATABASE
            
            data = request.get_json()
            template_name = data.get('name', '').strip()
            subject = data.get('subject', '').strip()
            body = data.get('body', '').strip()
            html = data.get('html', '').strip()
            
            if not template_name or not subject or not body:
                return jsonify({
                    'success': False,
                    'error': 'Укажите название, тему и текст шаблона'
                }), 400
            
            conn = sqlite3.connect(DATABASE)
            cursor = conn.cursor()
            
            # Создаем таблицу если её нет
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS mail_templates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    subject TEXT NOT NULL,
                    body TEXT NOT NULL,
                    html TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Проверяем существует ли шаблон
            cursor.execute('SELECT id FROM mail_templates WHERE name = ?', (template_name,))
            existing = cursor.fetchone()
            
            if existing:
                # Обновляем
                cursor.execute('''
                    UPDATE mail_templates 
                    SET subject = ?, body = ?, html = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE name = ?
                ''', (subject, body, html, template_name))
                message = f'Шаблон "{template_name}" обновлен'
            else:
                # Создаем новый
                cursor.execute('''
                    INSERT INTO mail_templates (name, subject, body, html)
                    VALUES (?, ?, ?, ?)
                ''', (template_name, subject, body, html))
                message = f'Шаблон "{template_name}" сохранен'
            
            conn.commit()
            conn.close()
            
            return jsonify({
                'success': True,
                'message': message
            })
        
        except Exception as e:
            logger.error(f"Ошибка при сохранении шаблона: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/api/mail-sender/templates-list', methods=['GET'])
    @login_required
    def get_templates_list():
        """Получить список всех сохраненных шаблонов"""
        try:
            import sqlite3
            from config import DATABASE
            
            conn = sqlite3.connect(DATABASE)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Создаем таблицу если её нет
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS mail_templates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    subject TEXT NOT NULL,
                    body TEXT NOT NULL,
                    html TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('SELECT id, name, subject, body, html, updated_at FROM mail_templates ORDER BY updated_at DESC')
            rows = cursor.fetchall()
            conn.close()
            
            templates = [dict(row) for row in rows]
            
            return jsonify({
                'success': True,
                'templates': templates,
                'count': len(templates)
            })
        
        except Exception as e:
            logger.error(f"Ошибка при получении шаблонов: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/api/mail-sender/load-template/<int:template_id>', methods=['GET'])
    @login_required
    def load_template(template_id):
        """Загрузить шаблон по ID"""
        try:
            import sqlite3
            from config import DATABASE
            
            conn = sqlite3.connect(DATABASE)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('SELECT id, name, subject, body, html FROM mail_templates WHERE id = ?', (template_id,))
            row = cursor.fetchone()
            conn.close()
            
            if not row:
                return jsonify({
                    'success': False,
                    'error': 'Шаблон не найден'
                }), 404
            
            template = dict(row)
            
            return jsonify({
                'success': True,
                'template': template
            })
        
        except Exception as e:
            logger.error(f"Ошибка при загрузке шаблона: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/api/mail-sender/delete-template/<int:template_id>', methods=['DELETE'])
    @login_required
    def delete_template(template_id):
        """Удалить шаблон"""
        try:
            import sqlite3
            from config import DATABASE
            
            conn = sqlite3.connect(DATABASE)
            cursor = conn.cursor()
            
            cursor.execute('SELECT name FROM mail_templates WHERE id = ?', (template_id,))
            template = cursor.fetchone()
            
            if not template:
                conn.close()
                return jsonify({
                    'success': False,
                    'error': 'Шаблон не найден'
                }), 404
            
            cursor.execute('DELETE FROM mail_templates WHERE id = ?', (template_id,))
            conn.commit()
            conn.close()
            
            return jsonify({
                'success': True,
                'message': f'Шаблон "{template[0]}" удален'
            })
        
        except Exception as e:
            logger.error(f"Ошибка при удалении шаблона: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
