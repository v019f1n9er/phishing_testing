"""
Минимальный почтовый клиент с поддержкой IMAP и POP3
"""

import imaplib
import poplib
import email
from email.header import decode_header
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import ssl


@dataclass
class MailAccount:
    """Класс для хранения информации о почтовой учетной записи"""
    email_address: str
    password: str
    imap_server: Optional[str] = None
    imap_port: int = 993
    pop3_server: Optional[str] = None
    pop3_port: int = 995
    protocol: str = "IMAP"  # IMAP или POP3
    use_ssl: bool = True
    timeout: int = 10


@dataclass
class Email:
    """Класс для представления письма"""
    sender: str
    subject: str
    body: str
    html: Optional[str] = None
    date: Optional[str] = None
    message_id: Optional[str] = None
    uid: Optional[str] = None


class IMAPClient:
    """Клиент для работы с IMAP почтой"""
    
    def __init__(self, account: MailAccount):
        self.account = account
        self.connection = None
        
    def connect(self) -> bool:
        """Подключиться к IMAP серверу"""
        try:
            if self.account.use_ssl:
                context = ssl.create_default_context()
                self.connection = imaplib.IMAP4_SSL(
                    self.account.imap_server,
                    self.account.imap_port,
                    timeout=self.account.timeout,
                    ssl_context=context
                )
            else:
                self.connection = imaplib.IMAP4(
                    self.account.imap_server,
                    self.account.imap_port,
                    timeout=self.account.timeout
                )
            
            # Логинимся
            self.connection.login(self.account.email_address, self.account.password)
            return True
        except Exception as e:
            print(f"Ошибка подключения к IMAP: {e}")
            return False
    
    def disconnect(self):
        """Отключиться от сервера"""
        try:
            if self.connection:
                self.connection.close()
                self.connection = None
        except Exception as e:
            print(f"Ошибка при отключении: {e}")
    
    def get_mailboxes(self) -> List[str]:
        """Получить список почтовых ящиков"""
        try:
            status, mailboxes = self.connection.list()
            if status == 'OK':
                return [mailbox.decode().split('"')[-2] for mailbox in mailboxes]
            return []
        except Exception as e:
            print(f"Ошибка при получении ящиков: {e}")
            return []
    
    def select_mailbox(self, mailbox: str = "INBOX") -> bool:
        """Выбрать почтовый ящик"""
        try:
            status, _ = self.connection.select(mailbox)
            return status == 'OK'
        except Exception as e:
            print(f"Ошибка при выборе ящика: {e}")
            return False
    
    def get_emails(self, mailbox: str = "INBOX", limit: int = 10) -> List[Email]:
        """Получить список писем из ящика"""
        emails = []
        try:
            if not self.select_mailbox(mailbox):
                return emails
            
            # Ищем все письма
            status, message_ids = self.connection.search(None, "ALL")
            
            if status != 'OK':
                return emails
            
            # Берем последние письма (до limit)
            id_list = message_ids[0].split()
            id_list = id_list[-limit:] if len(id_list) > limit else id_list
            
            for msg_id in id_list:
                try:
                    status, msg_data = self.connection.fetch(msg_id, "(RFC822)")
                    
                    if status == 'OK':
                        email_body = msg_data[0][1]
                        msg = email.message_from_bytes(email_body)
                        
                        email_obj = self._parse_email(msg, msg_id)
                        emails.append(email_obj)
                except Exception as e:
                    print(f"Ошибка при парсинге письма: {e}")
                    continue
            
            return emails
        except Exception as e:
            print(f"Ошибка при получении писем: {e}")
            return emails
    
    def _parse_email(self, msg: email.message.Message, uid: bytes) -> Email:
        """Парсить сырое письмо в объект Email"""
        sender = msg.get("From", "Unknown")
        subject = self._decode_header(msg.get("Subject", ""))
        date = msg.get("Date", "")
        message_id = msg.get("Message-ID", "")
        
        body = ""
        html = None
        
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition", ""))
                
                if "attachment" not in content_disposition:
                    if content_type == "text/plain":
                        try:
                            body = part.get_payload(decode=True).decode()
                        except:
                            body = part.get_payload()
                    elif content_type == "text/html":
                        try:
                            html = part.get_payload(decode=True).decode()
                        except:
                            html = part.get_payload()
        else:
            try:
                body = msg.get_payload(decode=True).decode()
            except:
                body = msg.get_payload()
        
        return Email(
            sender=sender,
            subject=subject,
            body=body,
            html=html,
            date=date,
            message_id=message_id,
            uid=uid.decode() if isinstance(uid, bytes) else uid
        )
    
    @staticmethod
    def _decode_header(header: str) -> str:
        """Декодировать заголовок письма"""
        try:
            decoded_parts = decode_header(header)
            result = ""
            for part, encoding in decoded_parts:
                if isinstance(part, bytes):
                    result += part.decode(encoding or 'utf-8', errors='ignore')
                else:
                    result += part
            return result
        except:
            return header


class POP3Client:
    """Клиент для работы с POP3 почтой"""
    
    def __init__(self, account: MailAccount):
        self.account = account
        self.connection = None
    
    def connect(self) -> bool:
        """Подключиться к POP3 серверу"""
        try:
            if self.account.use_ssl:
                self.connection = poplib.POP3_SSL(
                    self.account.pop3_server,
                    self.account.pop3_port,
                    timeout=self.account.timeout
                )
            else:
                self.connection = poplib.POP3(
                    self.account.pop3_server,
                    self.account.pop3_port,
                    timeout=self.account.timeout
                )
            
            # Логинимся
            self.connection.user(self.account.email_address)
            self.connection.pass_(self.account.password)
            return True
        except Exception as e:
            print(f"Ошибка подключения к POP3: {e}")
            return False
    
    def disconnect(self):
        """Отключиться от сервера"""
        try:
            if self.connection:
                self.connection.quit()
                self.connection = None
        except Exception as e:
            print(f"Ошибка при отключении: {e}")
    
    def get_emails(self, limit: int = 10) -> List[Email]:
        """Получить список писем (POP3 не поддерживает папки)"""
        emails = []
        try:
            stat = self.connection.stat()
            num_emails = stat[0]
            
            # Берем последние письма (до limit)
            start = max(1, num_emails - limit + 1)
            
            for i in range(start, num_emails + 1):
                try:
                    status, msg_data, octets = self.connection.retr(i)
                    
                    if status == b'+OK':
                        email_body = b'\r\n'.join(msg_data)
                        msg = email.message_from_bytes(email_body)
                        
                        email_obj = self._parse_email(msg, str(i))
                        emails.append(email_obj)
                except Exception as e:
                    print(f"Ошибка при парсинге письма: {e}")
                    continue
            
            return emails
        except Exception as e:
            print(f"Ошибка при получении писем: {e}")
            return emails
    
    def _parse_email(self, msg: email.message.Message, uid: str) -> Email:
        """Парсить сырое письмо в объект Email"""
        sender = msg.get("From", "Unknown")
        subject = self._decode_header(msg.get("Subject", ""))
        date = msg.get("Date", "")
        message_id = msg.get("Message-ID", "")
        
        body = ""
        html = None
        
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition", ""))
                
                if "attachment" not in content_disposition:
                    if content_type == "text/plain":
                        try:
                            body = part.get_payload(decode=True).decode()
                        except:
                            body = part.get_payload()
                    elif content_type == "text/html":
                        try:
                            html = part.get_payload(decode=True).decode()
                        except:
                            html = part.get_payload()
        else:
            try:
                body = msg.get_payload(decode=True).decode()
            except:
                body = msg.get_payload()
        
        return Email(
            sender=sender,
            subject=subject,
            body=body,
            html=html,
            date=date,
            message_id=message_id,
            uid=uid
        )
    
    @staticmethod
    def _decode_header(header: str) -> str:
        """Декодировать заголовок письма"""
        try:
            decoded_parts = decode_header(header)
            result = ""
            for part, encoding in decoded_parts:
                if isinstance(part, bytes):
                    result += part.decode(encoding or 'utf-8', errors='ignore')
                else:
                    result += part
            return result
        except:
            return header


class MailClientManager:
    """Менеджер для управления почтовыми учетными записями"""
    
    def __init__(self):
        self.accounts: Dict[str, MailAccount] = {}
        self.clients: Dict[str, any] = {}
    
    def add_account(
        self,
        email_address: str,
        password: str,
        protocol: str = "IMAP",
        imap_server: Optional[str] = None,
        imap_port: int = 993,
        pop3_server: Optional[str] = None,
        pop3_port: int = 995,
        use_ssl: bool = True
    ) -> bool:
        """Добавить новую почтовую учетную запись"""
        try:
            account = MailAccount(
                email_address=email_address,
                password=password,
                imap_server=imap_server,
                imap_port=imap_port,
                pop3_server=pop3_server,
                pop3_port=pop3_port,
                protocol=protocol.upper(),
                use_ssl=use_ssl
            )
            
            # Проверяем подключение
            if account.protocol == "IMAP":
                if not imap_server:
                    print("Ошибка: imap_server не указан для IMAP")
                    return False
                client = IMAPClient(account)
            else:  # POP3
                if not pop3_server:
                    print("Ошибка: pop3_server не указан для POP3")
                    return False
                client = POP3Client(account)
            
            if not client.connect():
                return False
            
            client.disconnect()
            
            # Сохраняем учетную запись
            self.accounts[email_address] = account
            return True
        except Exception as e:
            print(f"Ошибка при добавлении учетной записи: {e}")
            return False
    
    def remove_account(self, email_address: str) -> bool:
        """Удалить почтовую учетную запись"""
        try:
            if email_address in self.accounts:
                # Закрываем соединение если оно открыто
                if email_address in self.clients:
                    self.clients[email_address].disconnect()
                    del self.clients[email_address]
                
                del self.accounts[email_address]
                return True
            return False
        except Exception as e:
            print(f"Ошибка при удалении учетной записи: {e}")
            return False
    
    def get_client(self, email_address: str) -> Optional[any]:
        """Получить клиент для учетной записи"""
        if email_address not in self.accounts:
            return None
        
        if email_address not in self.clients:
            account = self.accounts[email_address]
            
            if account.protocol == "IMAP":
                client = IMAPClient(account)
            else:  # POP3
                client = POP3Client(account)
            
            self.clients[email_address] = client
        
        return self.clients[email_address]
    
    def list_accounts(self) -> List[Dict[str, any]]:
        """Получить список всех учетных записей"""
        return [
            {
                "email": addr,
                "protocol": acc.protocol,
                "server": acc.imap_server or acc.pop3_server
            }
            for addr, acc in self.accounts.items()
        ]
    
    def get_emails(self, email_address: str, limit: int = 10) -> List[Email]:
        """Получить письма из учетной записи"""
        client = self.get_client(email_address)
        if not client:
            print(f"Учетная запись {email_address} не найдена")
            return []
        
        if not client.connect():
            return []
        
        try:
            emails = client.get_emails(limit=limit)
            return emails
        finally:
            client.disconnect()


# Пример использования
if __name__ == "__main__":
    # Создаем менеджер
    manager = MailClientManager()
    
    # Добавляем IMAP учетную запись (пример)
    # manager.add_account(
    #     email_address="user@gmail.com",
    #     password="your_app_password",
    #     protocol="IMAP",
    #     imap_server="imap.gmail.com",
    #     imap_port=993
    # )
    
    # Добавляем POP3 учетную запись (пример)
    # manager.add_account(
    #     email_address="user@mail.com",
    #     password="your_password",
    #     protocol="POP3",
    #     pop3_server="pop.mail.com",
    #     pop3_port=995
    # )
    
    # Выводим список учетных записей
    print("Учетные записи:")
    for account in manager.list_accounts():
        print(f"  - {account['email']} ({account['protocol']})")
    
    # Получаем письма
    # emails = manager.get_emails("user@gmail.com", limit=5)
    # for email_obj in emails:
    #     print(f"\nОтправитель: {email_obj.sender}")
    #     print(f"Тема: {email_obj.subject}")
    #     print(f"Тело: {email_obj.body[:100]}...")
