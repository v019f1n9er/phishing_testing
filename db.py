import os
import sqlite3
from datetime import datetime
from werkzeug.security import generate_password_hash
from config import DATABASE

def initialize_db():
    if not os.path.exists(DATABASE):
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE clicks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                ip TEXT,
                user_agent TEXT,
                token TEXT
            )
        ''')
        conn.commit()
        conn.close()

def initialize_users():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT
        )
    ''')

    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        cursor.execute(
            "INSERT INTO users VALUES (NULL, ?, ?, ?)",
            (
                'admin',
                generate_password_hash('passwd123'),
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            )
        )

    conn.commit()
    conn.close()

def initialize_emails():
    import hashlib
    import secrets

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS emails (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            token TEXT UNIQUE NOT NULL,
            created_at TEXT
        )
    ''')

    cursor.execute("PRAGMA table_info(emails)")
    columns = [c[1] for c in cursor.fetchall()]

    if 'token' not in columns:
        cursor.execute("ALTER TABLE emails ADD COLUMN token TEXT")

    cursor.execute("SELECT id, email FROM emails WHERE token IS NULL OR token = ''")
    rows = cursor.fetchall()

    for row_id, email in rows:
        token = hashlib.md5(
            f"{email}_{row_id}_{secrets.token_hex(8)}".encode()
        ).hexdigest()[:16]
        cursor.execute(
            "UPDATE emails SET token = ? WHERE id = ?",
            (token, row_id)
        )

    conn.commit()
    conn.close()

def migrate_clicks_add_email_id():
    """
    Добавляет email_id в clicks, если его еще нет
    """
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute("PRAGMA table_info(clicks)")
    columns = [c[1] for c in cursor.fetchall()]

    if 'email_id' not in columns:
        cursor.execute("ALTER TABLE clicks ADD COLUMN email_id INTEGER")

    conn.commit()
    conn.close()
