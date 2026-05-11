"""
Модуль для отправки писем через SMTP
"""

import smtplib
import sqlite3
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Optional, Dict
from dataclasses import dataclass
from datetime import datetime
from mail_accounts_api import get_mail_account
import logging

logger = logging.getLogger(__name__)
DB_PATH = os.getenv('DATABASE_PATH', 'phishing.db')

# Маппинг SMTP серверов для известных сервисов
SMTP_CONFIG = {
    'gmail': {'host': 'smtp.gmail.com', 'port': 587},
    'outlook': {'host': 'smtp.office365.com', 'port': 587},
    'mail_ru': {'host': 'smtp.mail.ru', 'port': 587},
    'yandex': {'host': 'smtp.yandex.com', 'port': 587},
    'yahoo': {'host': 'smtp.mail.yahoo.com', 'port': 587},
}


@dataclass
class EmailMessage:
    """Класс для представления письма для отправки"""
    recipient: str
    subject: str
    body: str
    html: Optional[str] = None
    from_account_id: int = None


class SMTPMailSender:
    """Отправка писем через SMTP"""
    
    def __init__(self, account_id: int):
        """
        Инициализировать отправителя
        
        Args:
            account_id: ID почтовой учетной записи из БД
        """
        self.account_id = account_id
        self.account = get_mail_account(account_id)
        
        if not self.account:
            raise ValueError(f"Учетная запись с ID {account_id} не найдена")
        
        self.connection = None
    
    def _guess_smtp_server(self) -> tuple:
        """Определить SMTP сервер по адресу электронной почты"""
        email = self.account.email_address
        domain = email.split('@')[1].lower()
        
        # Проверяем известные сервисы
        for service, config in SMTP_CONFIG.items():
            if service in domain or domain in self.account.imap_server or '':
                return config['host'], config['port']
        
        # Попытка использовать стандартный SMTP с заменой IMAP на SMTP
        if self.account.imap_server:
            smtp_host = self.account.imap_server.replace('imap.', 'smtp.')
            return smtp_host, 587
        
        raise ValueError(f"Не удалось определить SMTP сервер для {email}")
    
    def connect(self) -> bool:
        """Подключиться к SMTP серверу"""
        try:
            smtp_host, smtp_port = self._guess_smtp_server()
            
            # Используем TLS (STARTTLS)
            self.connection = smtplib.SMTP(smtp_host, smtp_port, timeout=10)
            self.connection.starttls()
            
            # Логинимся
            self.connection.login(
                self.account.email_address,
                self.account.password
            )
            
            logger.info(f"Подключение SMTP успешно для {self.account.email_address}")
            return True
        
        except Exception as e:
            logger.error(f"Ошибка подключения SMTP: {e}")
            return False
    
    def disconnect(self):
        """Отключиться от SMTP сервера"""
        try:
            if self.connection:
                self.connection.quit()
                self.connection = None
        except Exception as e:
            logger.error(f"Ошибка при отключении SMTP: {e}")
    
    def send_email(self, message: EmailMessage) -> bool:
        """
        Отправить письмо
        
        Args:
            message: объект EmailMessage
            
        Returns:
            True если успешно, False если ошибка
        """
        try:
            if not self.connection:
                if not self.connect():
                    return False
            
            # Создаем письмо
            msg = MIMEMultipart('alternative')
            msg['Subject'] = message.subject
            msg['From'] = self.account.email_address
            msg['To'] = message.recipient
            
            # Добавляем текст
            if message.body:
                msg.attach(MIMEText(message.body, 'plain', 'utf-8'))
            
            # Добавляем HTML если есть
            if message.html:
                msg.attach(MIMEText(message.html, 'html', 'utf-8'))
            
            # Отправляем
            self.connection.send_message(msg)
            
            logger.info(f"Письмо отправлено на {message.recipient}")
            return True
        
        except smtplib.SMTPAuthenticationError:
            logger.error(f"Ошибка аутентификации SMTP для {self.account.email_address}")
            return False
        except Exception as e:
            logger.error(f"Ошибка при отправке письма: {e}")
            return False
    
    def send_bulk_emails(self, messages: List[EmailMessage]) -> Dict[str, int]:
        """
        Отправить множество писем
        
        Args:
            messages: список EmailMessage
            
        Returns:
            Словарь со статистикой {'sent': X, 'failed': Y}
        """
        stats = {'sent': 0, 'failed': 0}
        
        if not self.connect():
            stats['failed'] = len(messages)
            return stats
        
        try:
            for msg in messages:
                if self.send_email(msg):
                    stats['sent'] += 1
                else:
                    stats['failed'] += 1
        finally:
            self.disconnect()
        
        return stats


def init_mail_sending_tables():
    """Инициализировать таблицы для отправки писем"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Таблица для кампаний отправки
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS mail_campaigns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                from_account_id INTEGER NOT NULL,
                subject TEXT NOT NULL,
                body TEXT,
                html TEXT,
                recipient_count INTEGER DEFAULT 0,
                sent_count INTEGER DEFAULT 0,
                failed_count INTEGER DEFAULT 0,
                status TEXT DEFAULT 'draft',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                started_at TIMESTAMP,
                completed_at TIMESTAMP,
                FOREIGN KEY (from_account_id) REFERENCES mail_accounts(id)
            )
        ''')
        
        # Таблица для расписания отправки
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS mail_schedule (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                campaign_id INTEGER NOT NULL,
                recipient_email TEXT NOT NULL,
                scheduled_time TIMESTAMP,
                sent_time TIMESTAMP,
                status TEXT DEFAULT 'pending',
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (campaign_id) REFERENCES mail_campaigns(id)
            )
        ''')
        
        # Таблица для уведомлений
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS mail_notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                campaign_id INTEGER,
                recipient_email TEXT,
                scheduled_time TIMESTAMP,
                sent_time TIMESTAMP,
                status TEXT,
                message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (campaign_id) REFERENCES mail_campaigns(id)
            )
        ''')
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Ошибка инициализации таблиц: {e}")
        return False
