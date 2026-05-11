"""
API endpoints для управления почтовыми учетными записями
"""

from flask import request, jsonify
from security import login_required
import sqlite3
import json
from mail_client import MailClientManager, MailAccount, IMAPClient, POP3Client
import os


# Инициализируем глобальный менеджер
mail_manager = MailClientManager()
DB_PATH = os.getenv('DATABASE_PATH', 'phishing.db')


def init_mail_accounts_table():
    """Инициализировать таблицу для хранения почтовых учетных записей"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS mail_accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email_address TEXT UNIQUE NOT NULL,
                password_encrypted TEXT NOT NULL,
                protocol TEXT NOT NULL,
                server TEXT NOT NULL,
                port INTEGER NOT NULL,
                use_ssl BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_sync TIMESTAMP,
                status TEXT DEFAULT 'disconnected'
            )
        ''')
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Ошибка инициализации таблицы: {e}")
        return False


def _get_encryption_key():
    """Получить ключ шифрования"""
    # Простое шифрование XOR (для продакшена использовать Fernet)
    return "phishing_testing_key_12345"


def _encrypt_password(password: str) -> str:
    """Зашифровать пароль"""
    key = _get_encryption_key()
    encrypted = ''.join(chr(ord(p) ^ ord(key[i % len(key)])) for i, p in enumerate(password))
    return encrypted


def _decrypt_password(encrypted: str) -> str:
    """Расшифровать пароль"""
    key = _get_encryption_key()
    decrypted = ''.join(chr(ord(e) ^ ord(key[i % len(key)])) for i, e in enumerate(encrypted))
    return decrypted


def _save_account_to_db(email: str, password: str, protocol: str, server: str, port: int, use_ssl: bool):
    """Сохранить учетную запись в БД"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        encrypted_password = _encrypt_password(password)
        
        cursor.execute('''
            INSERT OR REPLACE INTO mail_accounts 
            (email_address, password_encrypted, protocol, server, port, use_ssl, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (email, encrypted_password, protocol, server, port, use_ssl, 'disconnected'))
        
        conn.commit()
        account_id = cursor.lastrowid
        conn.close()
        
        return True, account_id
    except sqlite3.IntegrityError:
        return False, "Эта учетная запись уже добавлена"
    except Exception as e:
        return False, str(e)


def _get_account_from_db(account_id: int):
    """Получить учетную запись из БД"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM mail_accounts WHERE id = ?
        ''', (account_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return dict(row)
        return None
    except Exception as e:
        print(f"Ошибка получения учетной записи: {e}")
        return None


def _get_all_accounts_from_db():
    """Получить все учетные записи из БД"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM mail_accounts ORDER BY created_at DESC
        ''')
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    except Exception as e:
        print(f"Ошибка получения учетных записей: {e}")
        return []


def _delete_account_from_db(account_id: int):
    """Удалить учетную запись из БД"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM mail_accounts WHERE id = ?', (account_id,))
        
        conn.commit()
        conn.close()
        
        return True
    except Exception as e:
        print(f"Ошибка удаления учетной записи: {e}")
        return False


def _update_account_status(account_id: int, status: str):
    """Обновить статус учетной записи"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE mail_accounts SET status = ? WHERE id = ?
        ''', (status, account_id))
        
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Ошибка обновления статуса: {e}")


def register_mail_accounts_routes(app):
    """Зарегистрировать маршруты для управления почтовыми учетными записями"""
    
    # Инициализируем таблицу при запуске
    init_mail_accounts_table()
    
    @app.route('/mail-accounts')
    @login_required
    def mail_accounts_page():
        """Страница управления почтовыми учетными записями"""
        from flask import render_template
        return render_template('mail_accounts.html')
    
    @app.route('/api/mail-accounts/add', methods=['POST'])
    @login_required
    def add_mail_account():
        """Добавить новую почтовую учетную запись"""
        try:
            data = request.get_json()
            
            email = data.get('email_address', '').strip()
            password = data.get('password', '')
            protocol = data.get('protocol', 'IMAP').upper()
            server = data.get('server', '').strip()
            port = data.get('port', 993)
            use_ssl = data.get('use_ssl', True)
            
            # Валидация
            if not all([email, password, protocol, server, port]):
                return jsonify({
                    'success': False,
                    'error': 'Не все поля заполнены'
                }), 400
            
            if protocol not in ['IMAP', 'POP3']:
                return jsonify({
                    'success': False,
                    'error': 'Неправильный протокол'
                }), 400
            
            # Создаем временный объект учетной записи для проверки подключения
            temp_account = MailAccount(
                email_address=email,
                password=password,
                imap_server=server if protocol == 'IMAP' else None,
                imap_port=port if protocol == 'IMAP' else 993,
                pop3_server=server if protocol == 'POP3' else None,
                pop3_port=port if protocol == 'POP3' else 995,
                protocol=protocol,
                use_ssl=use_ssl
            )
            
            # Тестируем подключение
            if protocol == 'IMAP':
                client = IMAPClient(temp_account)
            else:
                client = POP3Client(temp_account)
            
            if not client.connect():
                return jsonify({
                    'success': False,
                    'error': 'Не удалось подключиться. Проверьте учетные данные и параметры сервера.'
                }), 400
            
            client.disconnect()
            
            # Сохраняем в БД
            success, result = _save_account_to_db(email, password, protocol, server, port, use_ssl)
            
            if not success:
                return jsonify({
                    'success': False,
                    'error': result
                }), 400
            
            return jsonify({
                'success': True,
                'message': f'Учетная запись {email} успешно добавлена',
                'id': result
            })
        
        except Exception as e:
            print(f"Ошибка при добавлении учетной записи: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/api/mail-accounts/list', methods=['GET'])
    @login_required
    def list_mail_accounts():
        """Получить список всех почтовых учетных записей"""
        try:
            accounts = _get_all_accounts_from_db()
            
            # Не отправляем пароли на клиент
            accounts_safe = []
            for acc in accounts:
                accounts_safe.append({
                    'id': acc['id'],
                    'email': acc['email_address'],
                    'protocol': acc['protocol'],
                    'server': acc['server'],
                    'port': acc['port'],
                    'status': acc['status']
                })
            
            return jsonify({
                'success': True,
                'accounts': accounts_safe
            })
        
        except Exception as e:
            print(f"Ошибка при получении списка учетных записей: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/api/mail-accounts/test/<int:account_id>', methods=['GET'])
    @login_required
    def test_mail_account(account_id):
        """Протестировать подключение учетной записи"""
        try:
            acc_data = _get_account_from_db(account_id)
            
            if not acc_data:
                return jsonify({
                    'success': False,
                    'error': 'Учетная запись не найдена'
                }), 404
            
            # Расшифровываем пароль
            password = _decrypt_password(acc_data['password_encrypted'])
            
            # Создаем объект учетной записи
            account = MailAccount(
                email_address=acc_data['email_address'],
                password=password,
                imap_server=acc_data['server'] if acc_data['protocol'] == 'IMAP' else None,
                imap_port=acc_data['port'] if acc_data['protocol'] == 'IMAP' else 993,
                pop3_server=acc_data['server'] if acc_data['protocol'] == 'POP3' else None,
                pop3_port=acc_data['port'] if acc_data['protocol'] == 'POP3' else 995,
                protocol=acc_data['protocol'],
                use_ssl=bool(acc_data['use_ssl'])
            )
            
            # Подключаемся
            if account.protocol == 'IMAP':
                client = IMAPClient(account)
            else:
                client = POP3Client(account)
            
            if client.connect():
                _update_account_status(account_id, 'connected')
                client.disconnect()
                return jsonify({
                    'success': True,
                    'message': 'Подключение успешно'
                })
            else:
                _update_account_status(account_id, 'disconnected')
                return jsonify({
                    'success': False,
                    'error': 'Не удалось подключиться'
                }), 400
        
        except Exception as e:
            print(f"Ошибка при тестировании учетной записи: {e}")
            _update_account_status(account_id, 'disconnected')
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/api/mail-accounts/delete/<int:account_id>', methods=['DELETE'])
    @login_required
    def delete_mail_account(account_id):
        """Удалить почтовую учетную запись"""
        try:
            if _delete_account_from_db(account_id):
                return jsonify({
                    'success': True,
                    'message': 'Учетная запись удалена'
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'Ошибка удаления учетной записи'
                }), 500
        
        except Exception as e:
            print(f"Ошибка при удалении учетной записи: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500


# Функция для получения учетной записи для использования в других модулях
def get_mail_account(account_id: int):
    """Получить объект MailAccount по ID"""
    acc_data = _get_account_from_db(account_id)
    
    if not acc_data:
        return None
    
    password = _decrypt_password(acc_data['password_encrypted'])
    
    return MailAccount(
        email_address=acc_data['email_address'],
        password=password,
        imap_server=acc_data['server'] if acc_data['protocol'] == 'IMAP' else None,
        imap_port=acc_data['port'] if acc_data['protocol'] == 'IMAP' else 993,
        pop3_server=acc_data['server'] if acc_data['protocol'] == 'POP3' else None,
        pop3_port=acc_data['port'] if acc_data['protocol'] == 'POP3' else 995,
        protocol=acc_data['protocol'],
        use_ssl=bool(acc_data['use_ssl'])
    )
