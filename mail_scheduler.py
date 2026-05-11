"""
Модуль планировщика для управления отправкой писем
"""

import sqlite3
import os
import random
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from mail_sender import SMTPMailSender, EmailMessage
import logging
import threading
import time

logger = logging.getLogger(__name__)
DB_PATH = os.getenv('DATABASE_PATH', 'phishing.db')


class MailScheduler:
    """Планировщик для управления отправкой писем"""
    
    def __init__(self):
        """Инициализировать планировщик"""
        self.running_tasks = {}  # {campaign_id: task_info}
        self.scheduler_thread = None
    
    def create_campaign(
        self,
        name: str,
        from_account_id: int,
        subject: str,
        body: str,
        recipients: List[str],
        html: Optional[str] = None
    ) -> Optional[int]:
        """
        Создать кампанию отправки
        
        Args:
            name: Название кампании
            from_account_id: ID отправителя
            subject: Тема письма
            body: Текст письма
            recipients: Список адресов получателей
            html: HTML версия письма (опционально)
            
        Returns:
            ID созданной кампании или None
        """
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # Создаем кампанию
            cursor.execute('''
                INSERT INTO mail_campaigns 
                (name, from_account_id, subject, body, html, recipient_count, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (name, from_account_id, subject, body, html, len(recipients), 'draft'))
            
            campaign_id = cursor.lastrowid
            
            # Добавляем получателей
            for recipient in recipients:
                cursor.execute('''
                    INSERT INTO mail_schedule (campaign_id, recipient_email, status)
                    VALUES (?, ?, ?)
                ''', (campaign_id, recipient, 'pending'))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Кампания {campaign_id} создана с {len(recipients)} получателями")
            return campaign_id
        
        except Exception as e:
            logger.error(f"Ошибка при создании кампании: {e}")
            return None
    
    def schedule_emails(
        self,
        campaign_id: int,
        start_date: datetime,
        end_date: datetime,
        random_schedule: bool = True,
        require_confirmation: bool = False
    ) -> Dict[str, any]:
        """
        Планировать отправку писем
        
        Args:
            campaign_id: ID кампании
            start_date: Начальная дата отправки
            end_date: Конечная дата отправки
            random_schedule: Распределить по случайным датам
            require_confirmation: Требовать подтверждение от пользователя
            
        Returns:
            Словарь с информацией о планировании
        """
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # Получаем всех получателей
            cursor.execute('''
                SELECT id FROM mail_schedule WHERE campaign_id = ? AND status = 'pending'
            ''', (campaign_id,))
            
            recipients = cursor.fetchall()
            
            if not recipients:
                conn.close()
                return {'success': False, 'error': 'Нет получателей'}
            
            total_time = (end_date - start_date).total_seconds()
            
            scheduled_count = 0
            schedule_info = []
            
            for i, (schedule_id,) in enumerate(recipients):
                if random_schedule:
                    # Случайное время в диапазоне
                    random_seconds = random.randint(0, int(total_time))
                    scheduled_time = start_date + timedelta(seconds=random_seconds)
                else:
                    # Равномерное распределение
                    step = total_time / max(len(recipients), 1)
                    scheduled_time = start_date + timedelta(seconds=step * i)
                
                cursor.execute('''
                    UPDATE mail_schedule SET scheduled_time = ? WHERE id = ?
                ''', (scheduled_time, schedule_id))
                
                scheduled_count += 1
                
                # Получаем информацию для возврата
                cursor.execute('''
                    SELECT recipient_email FROM mail_schedule WHERE id = ?
                ''', (schedule_id,))
                
                email = cursor.fetchone()[0]
                schedule_info.append({
                    'recipient': email,
                    'scheduled_time': scheduled_time.isoformat()
                })
            
            conn.commit()
            
            # Обновляем статус кампании
            cursor.execute('''
                UPDATE mail_campaigns SET status = ? WHERE id = ?
            ''', ('scheduled' if not require_confirmation else 'pending_confirmation', campaign_id))
            
            conn.commit()
            conn.close()
            
            return {
                'success': True,
                'campaign_id': campaign_id,
                'scheduled_count': scheduled_count,
                'require_confirmation': require_confirmation,
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'schedule_preview': schedule_info[:5]  # Первые 5 для превью
            }
        
        except Exception as e:
            logger.error(f"Ошибка при планировании отправки: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_campaign_schedule_preview(self, campaign_id: int, limit: int = 10) -> List[Dict]:
        """
        Получить превью расписания для кампании
        
        Args:
            campaign_id: ID кампании
            limit: Количество записей для показа
            
        Returns:
            Список запланированных отправок
        """
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT 
                    recipient_email, 
                    scheduled_time, 
                    status 
                FROM mail_schedule 
                WHERE campaign_id = ? 
                ORDER BY scheduled_time
                LIMIT ?
            ''', (campaign_id, limit))
            
            rows = cursor.fetchall()
            conn.close()
            
            return [dict(row) for row in rows]
        
        except Exception as e:
            logger.error(f"Ошибка при получении превью: {e}")
            return []
    
    def confirm_campaign(self, campaign_id: int) -> bool:
        """
        Подтвердить кампанию для отправки
        
        Args:
            campaign_id: ID кампании
            
        Returns:
            True если успешно
        """
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE mail_campaigns SET status = ? WHERE id = ?
            ''', ('scheduled', campaign_id))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Кампания {campaign_id} подтверждена для отправки")
            return True
        
        except Exception as e:
            logger.error(f"Ошибка при подтверждении: {e}")
            return False
    
    def start_campaign(self, campaign_id: int) -> bool:
        """
        Запустить кампанию отправки
        
        Args:
            campaign_id: ID кампании
            
        Returns:
            True если успешно
        """
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Получаем информацию о кампании
            cursor.execute('SELECT * FROM mail_campaigns WHERE id = ?', (campaign_id,))
            campaign = cursor.fetchone()
            
            if not campaign:
                conn.close()
                return False
            
            # Обновляем статус кампании
            cursor.execute('''
                UPDATE mail_campaigns 
                SET status = ?, started_at = ?
                WHERE id = ?
            ''', ('running', datetime.now(), campaign_id))
            
            conn.commit()
            conn.close()
            
            # Запускаем отправку в отдельном потоке
            thread = threading.Thread(
                target=self._execute_campaign,
                args=(campaign_id, dict(campaign))
            )
            thread.daemon = True
            thread.start()
            
            self.running_tasks[campaign_id] = {
                'thread': thread,
                'started_at': datetime.now()
            }
            
            logger.info(f"Кампания {campaign_id} запущена")
            return True
        
        except Exception as e:
            logger.error(f"Ошибка при запуске кампании: {e}")
            return False
    
    def _execute_campaign(self, campaign_id: int, campaign_data: Dict):
        """
        Выполнить отправку кампании (запускается в отдельном потоке)
        
        Args:
            campaign_id: ID кампании
            campaign_data: Данные кампании
        """
        try:
            sender = SMTPMailSender(campaign_data['from_account_id'])
            
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Получаем все запланированные отправки
            cursor.execute('''
                SELECT * FROM mail_schedule 
                WHERE campaign_id = ? AND status = 'pending'
                ORDER BY scheduled_time
            ''', (campaign_id,))
            
            schedules = cursor.fetchall()
            
            for schedule in schedules:
                scheduled_time = datetime.fromisoformat(schedule['scheduled_time'])
                now = datetime.now()
                
                # Ждем, пока не придет время отправки
                wait_seconds = (scheduled_time - now).total_seconds()
                
                if wait_seconds > 0:
                    time.sleep(wait_seconds)
                
                # Отправляем письмо
                message = EmailMessage(
                    recipient=schedule['recipient_email'],
                    subject=campaign_data['subject'],
                    body=campaign_data['body'],
                    html=campaign_data['html'],
                    from_account_id=campaign_data['from_account_id']
                )
                
                if sender.send_email(message):
                    status = 'sent'
                    sent_time = datetime.now()
                    error_msg = None
                else:
                    status = 'failed'
                    sent_time = datetime.now()
                    error_msg = 'Ошибка отправки'
                
                # Обновляем статус отправки
                cursor.execute('''
                    UPDATE mail_schedule 
                    SET status = ?, sent_time = ?, error_message = ?
                    WHERE id = ?
                ''', (status, sent_time, error_msg, schedule['id']))
                
                # Добавляем уведомление
                cursor.execute('''
                    INSERT INTO mail_notifications
                    (campaign_id, recipient_email, scheduled_time, sent_time, status, message)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    campaign_id,
                    schedule['recipient_email'],
                    scheduled_time,
                    sent_time,
                    status,
                    f"Письмо {'отправлено' if status == 'sent' else 'ошибка'}"
                ))
                
                conn.commit()
            
            sender.disconnect()
            
            # Обновляем статистику кампании
            cursor.execute('''
                SELECT 
                    SUM(CASE WHEN status = 'sent' THEN 1 ELSE 0 END) as sent,
                    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed
                FROM mail_schedule
                WHERE campaign_id = ?
            ''', (campaign_id,))
            
            stats = cursor.fetchone()
            
            cursor.execute('''
                UPDATE mail_campaigns 
                SET status = ?, completed_at = ?, 
                    sent_count = ?, failed_count = ?
                WHERE id = ?
            ''', (
                'completed',
                datetime.now(),
                stats['sent'] or 0,
                stats['failed'] or 0,
                campaign_id
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Кампания {campaign_id} завершена")
        
        except Exception as e:
            logger.error(f"Ошибка при выполнении кампании: {e}")
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE mail_campaigns SET status = ? WHERE id = ?
            ''', ('failed', campaign_id))
            conn.commit()
            conn.close()
    
    def get_campaign_status(self, campaign_id: int) -> Optional[Dict]:
        """
        Получить статус кампании
        
        Args:
            campaign_id: ID кампании
            
        Returns:
            Словарь с информацией о кампании
        """
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM mail_campaigns WHERE id = ?', (campaign_id,))
            campaign = cursor.fetchone()
            
            if not campaign:
                conn.close()
                return None
            
            # Получаем статистику
            cursor.execute('''
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'sent' THEN 1 ELSE 0 END) as sent,
                    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
                    SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending
                FROM mail_schedule
                WHERE campaign_id = ?
            ''', (campaign_id,))
            
            stats = cursor.fetchone()
            conn.close()
            
            return {
                'id': campaign['id'],
                'name': campaign['name'],
                'status': campaign['status'],
                'recipient_count': campaign['recipient_count'],
                'sent_count': campaign['sent_count'],
                'failed_count': campaign['failed_count'],
                'created_at': campaign['created_at'],
                'started_at': campaign['started_at'],
                'completed_at': campaign['completed_at'],
                'stats': {
                    'total': stats['total'],
                    'sent': stats['sent'],
                    'failed': stats['failed'],
                    'pending': stats['pending']
                }
            }
        
        except Exception as e:
            logger.error(f"Ошибка при получении статуса: {e}")
            return None
    
    def cancel_campaign(self, campaign_id: int) -> bool:
        """
        Отменить кампанию
        
        Args:
            campaign_id: ID кампании
            
        Returns:
            True если успешно
        """
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE mail_campaigns SET status = ? WHERE id = ?
            ''', ('cancelled', campaign_id))
            
            cursor.execute('''
                UPDATE mail_schedule SET status = 'cancelled' 
                WHERE campaign_id = ? AND status = 'pending'
            ''', (campaign_id,))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Кампания {campaign_id} отменена")
            return True
        
        except Exception as e:
            logger.error(f"Ошибка при отмене кампании: {e}")
            return False


# Глобальный экземпляр планировщика
scheduler = MailScheduler()
