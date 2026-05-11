"""
Модуль уведомлений для отправки писем
"""

import sqlite3
import os
from datetime import datetime
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)
DB_PATH = os.getenv('DATABASE_PATH', 'phishing.db')


class NotificationManager:
    """Менеджер уведомлений"""
    
    @staticmethod
    def get_notifications(
        campaign_id: Optional[int] = None,
        limit: int = 100,
        offset: int = 0,
        status_filter: Optional[str] = None
    ) -> List[Dict]:
        """
        Получить список уведомлений
        
        Args:
            campaign_id: ID кампании (опционально)
            limit: Максимальное количество
            offset: Смещение
            status_filter: Фильтр по статусу (sent, failed, pending)
            
        Returns:
            Список уведомлений
        """
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            query = 'SELECT * FROM mail_notifications WHERE 1=1'
            params = []
            
            if campaign_id:
                query += ' AND campaign_id = ?'
                params.append(campaign_id)
            
            if status_filter:
                query += ' AND status = ?'
                params.append(status_filter)
            
            query += ' ORDER BY created_at DESC LIMIT ? OFFSET ?'
            params.extend([limit, offset])
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            conn.close()
            
            return [dict(row) for row in rows]
        
        except Exception as e:
            logger.error(f"Ошибка при получении уведомлений: {e}")
            return []
    
    @staticmethod
    def get_campaign_notifications_summary(campaign_id: int) -> Dict:
        """
        Получить сводку уведомлений для кампании
        
        Args:
            campaign_id: ID кампании
            
        Returns:
            Словарь со статистикой
        """
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'sent' THEN 1 ELSE 0 END) as sent,
                    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
                    SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending
                FROM mail_notifications
                WHERE campaign_id = ?
            ''', (campaign_id,))
            
            result = cursor.fetchone()
            conn.close()
            
            return {
                'total': result[0] or 0,
                'sent': result[1] or 0,
                'failed': result[2] or 0,
                'pending': result[3] or 0
            }
        
        except Exception as e:
            logger.error(f"Ошибка при получении сводки: {e}")
            return {'total': 0, 'sent': 0, 'failed': 0, 'pending': 0}
    
    @staticmethod
    def format_notification(notification: Dict) -> str:
        """
        Форматировать уведомление для вывода
        
        Args:
            notification: Словарь уведомления
            
        Returns:
            Отформатированная строка
        """
        status_emoji = {
            'sent': '✅',
            'failed': '❌',
            'pending': '⏳'
        }
        
        status = notification.get('status', 'unknown')
        emoji = status_emoji.get(status, '❓')
        
        recipient = notification.get('recipient_email', 'Unknown')
        scheduled_time = notification.get('scheduled_time', 'N/A')
        sent_time = notification.get('sent_time', 'N/A')
        message = notification.get('message', '')
        
        return (
            f"{emoji} {status.upper()}\n"
            f"   Получатель: {recipient}\n"
            f"   Запланировано: {scheduled_time}\n"
            f"   Отправлено: {sent_time}\n"
            f"   Сообщение: {message}"
        )
    
    @staticmethod
    def get_failed_notifications(campaign_id: int) -> List[Dict]:
        """
        Получить все ошибки отправки для кампании
        
        Args:
            campaign_id: ID кампании
            
        Returns:
            Список ошибок
        """
        return NotificationManager.get_notifications(
            campaign_id=campaign_id,
            status_filter='failed'
        )
    
    @staticmethod
    def get_success_notifications(campaign_id: int) -> List[Dict]:
        """
        Получить все успешные отправки для кампании
        
        Args:
            campaign_id: ID кампании
            
        Returns:
            Список успешных отправок
        """
        return NotificationManager.get_notifications(
            campaign_id=campaign_id,
            status_filter='sent'
        )
    
    @staticmethod
    def export_notifications(campaign_id: int, format: str = 'json') -> Optional[str]:
        """
        Экспортировать уведомления в различные форматы
        
        Args:
            campaign_id: ID кампании
            format: Формат ('json', 'csv', 'txt')
            
        Returns:
            Строка с экспортированными данными
        """
        try:
            notifications = NotificationManager.get_notifications(campaign_id=campaign_id, limit=10000)
            
            if format == 'json':
                import json
                return json.dumps(notifications, ensure_ascii=False, indent=2)
            
            elif format == 'csv':
                import csv
                import io
                
                output = io.StringIO()
                if notifications:
                    writer = csv.DictWriter(
                        output,
                        fieldnames=notifications[0].keys()
                    )
                    writer.writeheader()
                    writer.writerows(notifications)
                
                return output.getvalue()
            
            elif format == 'txt':
                lines = []
                for notif in notifications:
                    lines.append(NotificationManager.format_notification(notif))
                    lines.append('-' * 60)
                
                return '\n'.join(lines)
            
            else:
                logger.error(f"Неизвестный формат экспорта: {format}")
                return None
        
        except Exception as e:
            logger.error(f"Ошибка при экспорте уведомлений: {e}")
            return None
    
    @staticmethod
    def get_notification_stats_by_hour(campaign_id: int) -> List[Dict]:
        """
        Получить статистику отправок по часам
        
        Args:
            campaign_id: ID кампании
            
        Returns:
            Список со статистикой по часам
        """
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT 
                    strftime('%Y-%m-%d %H:00:00', sent_time) as hour,
                    COUNT(*) as count,
                    SUM(CASE WHEN status = 'sent' THEN 1 ELSE 0 END) as sent,
                    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed
                FROM mail_notifications
                WHERE campaign_id = ? AND sent_time IS NOT NULL
                GROUP BY hour
                ORDER BY hour
            ''', (campaign_id,))
            
            rows = cursor.fetchall()
            conn.close()
            
            return [
                {
                    'hour': row[0],
                    'total': row[1],
                    'sent': row[2] or 0,
                    'failed': row[3] or 0
                }
                for row in rows
            ]
        
        except Exception as e:
            logger.error(f"Ошибка при получении статистики: {e}")
            return []
    
    @staticmethod
    def get_recent_notifications(limit: int = 20) -> List[Dict]:
        """
        Получить самые последние уведомления
        
        Args:
            limit: Максимальное количество
            
        Returns:
            Список последних уведомлений
        """
        return NotificationManager.get_notifications(limit=limit)


# Глобальный экземпляр менеджера
notification_manager = NotificationManager()
