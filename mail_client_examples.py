"""
Примеры использования почтового клиента
"""

from mail_client import MailClientManager, IMAPClient, POP3Client, MailAccount


def example_1_basic_usage():
    """Пример 1: Базовое использование с добавлением учетных записей"""
    manager = MailClientManager()
    
    # Добавляем IMAP учетную запись (Gmail)
    success = manager.add_account(
        email_address="your_email@gmail.com",
        password="your_app_password",  # Используйте пароль приложения для Gmail
        protocol="IMAP",
        imap_server="imap.gmail.com",
        imap_port=993,
        use_ssl=True
    )
    
    if success:
        print("✓ IMAP учетная запись добавлена успешно")
    else:
        print("✗ Ошибка при добавлении IMAP учетной записи")
    
    # Выводим список всех учетных записей
    print("\nДобавленные учетные записи:")
    for account in manager.list_accounts():
        print(f"  - {account['email']} ({account['protocol']}) - {account['server']}")


def example_2_imap_specific():
    """Пример 2: Работа с IMAP - получение писем из разных папок"""
    manager = MailClientManager()
    
    manager.add_account(
        email_address="user@gmail.com",
        password="app_password",
        protocol="IMAP",
        imap_server="imap.gmail.com",
        imap_port=993
    )
    
    # Получаем клиент и подключаемся
    client = manager.get_client("user@gmail.com")
    
    if client.connect():
        # Получаем список папок
        mailboxes = client.get_mailboxes()
        print("Доступные папки:")
        for mailbox in mailboxes:
            print(f"  - {mailbox}")
        
        # Получаем письма из INBOX
        print("\nПоследние письма из INBOX:")
        emails = client.get_emails(mailbox="INBOX", limit=5)
        
        for i, email_obj in enumerate(emails, 1):
            print(f"\n  {i}. От: {email_obj.sender}")
            print(f"     Тема: {email_obj.subject}")
            print(f"     Дата: {email_obj.date}")
            print(f"     Текст: {email_obj.body[:100]}...")
        
        client.disconnect()


def example_3_pop3_usage():
    """Пример 3: Использование POP3"""
    manager = MailClientManager()
    
    manager.add_account(
        email_address="user@mail.com",
        password="your_password",
        protocol="POP3",
        pop3_server="pop.mail.com",
        pop3_port=995,
        use_ssl=True
    )
    
    # Получаем письма через менеджер (удобный способ)
    emails = manager.get_emails("user@mail.com", limit=10)
    
    print(f"Получено писем: {len(emails)}")
    for i, email_obj in enumerate(emails, 1):
        print(f"\n{i}. {email_obj.subject}")
        print(f"   От: {email_obj.sender}")


def example_4_multiple_accounts():
    """Пример 4: Работа с несколькими учетными записями"""
    manager = MailClientManager()
    
    accounts = [
        {
            "email": "user1@gmail.com",
            "password": "password1",
            "protocol": "IMAP",
            "server": "imap.gmail.com"
        },
        {
            "email": "user2@outlook.com",
            "password": "password2",
            "protocol": "IMAP",
            "server": "outlook.office365.com"
        },
        {
            "email": "user3@mail.ru",
            "password": "password3",
            "protocol": "IMAP",
            "server": "imap.mail.ru"
        }
    ]
    
    for acc in accounts:
        success = manager.add_account(
            email_address=acc["email"],
            password=acc["password"],
            protocol=acc["protocol"],
            imap_server=acc["server"] if acc["protocol"] == "IMAP" else None,
            pop3_server=acc["server"] if acc["protocol"] == "POP3" else None,
        )
        if success:
            print(f"✓ {acc['email']} добавлена")
        else:
            print(f"✗ Ошибка при добавлении {acc['email']}")
    
    # Получаем письма из всех учетных записей
    for email_addr in manager.accounts.keys():
        print(f"\nПисьма от {email_addr}:")
        emails = manager.get_emails(email_addr, limit=3)
        for email_obj in emails:
            print(f"  - {email_obj.subject}")


def example_5_direct_client_usage():
    """Пример 5: Прямое использование клиента без менеджера"""
    account = MailAccount(
        email_address="user@gmail.com",
        password="app_password",
        imap_server="imap.gmail.com",
        imap_port=993,
        protocol="IMAP"
    )
    
    client = IMAPClient(account)
    
    if client.connect():
        # Получаем и выводим письма
        emails = client.get_emails(mailbox="INBOX", limit=3)
        
        for email_obj in emails:
            print(f"Subject: {email_obj.subject}")
            print(f"From: {email_obj.sender}")
            print(f"Body: {email_obj.body[:200]}...")
            print("---")
        
        client.disconnect()


def example_6_error_handling():
    """Пример 6: Обработка ошибок"""
    manager = MailClientManager()
    
    # Попытка добавить учетную запись с неправильными данными
    success = manager.add_account(
        email_address="invalid@example.com",
        password="wrong_password",
        protocol="IMAP",
        imap_server="imap.example.com",
        imap_port=993
    )
    
    if not success:
        print("Ошибка подключения - проверьте учетные данные")
    
    # Попытка получить письма из несуществующей учетной записи
    emails = manager.get_emails("nonexistent@example.com")
    if not emails:
        print("Учетная запись не найдена или письма отсутствуют")
    
    # Удаление учетной записи
    manager.remove_account("invalid@example.com")
    print("Учетная запись удалена")


# Конфигурации популярных почтовых сервисов
MAIL_SERVICES_CONFIG = {
    "gmail": {
        "imap_server": "imap.gmail.com",
        "imap_port": 993,
        "pop3_server": "pop.gmail.com",
        "pop3_port": 995,
        "note": "Используйте пароль приложения (App Password)"
    },
    "outlook": {
        "imap_server": "outlook.office365.com",
        "imap_port": 993,
        "pop3_server": "outlook.office365.com",
        "pop3_port": 995,
        "note": "Используйте пароль приложения если включена 2FA"
    },
    "mail_ru": {
        "imap_server": "imap.mail.ru",
        "imap_port": 993,
        "pop3_server": "pop.mail.ru",
        "pop3_port": 995,
    },
    "yandex": {
        "imap_server": "imap.yandex.com",
        "imap_port": 993,
        "pop3_server": "pop.yandex.com",
        "pop3_port": 995,
    },
    "yahoo": {
        "imap_server": "imap.mail.yahoo.com",
        "imap_port": 993,
        "pop3_server": "pop.mail.yahoo.com",
        "pop3_port": 995,
        "note": "Используйте пароль приложения (App Password)"
    }
}


def example_7_using_configs():
    """Пример 7: Использование конфигов для популярных сервисов"""
    manager = MailClientManager()
    
    # Добавляем Gmail
    config = MAIL_SERVICES_CONFIG["gmail"]
    manager.add_account(
        email_address="your_email@gmail.com",
        password="your_app_password",
        protocol="IMAP",
        imap_server=config["imap_server"],
        imap_port=config["imap_port"]
    )
    
    # Добавляем Yandex
    config = MAIL_SERVICES_CONFIG["yandex"]
    manager.add_account(
        email_address="your_email@yandex.com",
        password="your_password",
        protocol="IMAP",
        imap_server=config["imap_server"],
        imap_port=config["imap_port"]
    )
    
    print("Конфигурации почтовых сервисов:")
    for service, config in MAIL_SERVICES_CONFIG.items():
        print(f"\n{service.upper()}:")
        print(f"  IMAP: {config['imap_server']}:{config['imap_port']}")
        print(f"  POP3: {config['pop3_server']}:{config['pop3_port']}")
        if "note" in config:
            print(f"  Примечание: {config['note']}")


if __name__ == "__main__":
    print("Примеры использования почтового клиента")
    print("=" * 50)
    
    # Раскомментируйте нужный пример для запуска
    # example_1_basic_usage()
    # example_2_imap_specific()
    # example_3_pop3_usage()
    # example_4_multiple_accounts()
    # example_5_direct_client_usage()
    # example_6_error_handling()
    example_7_using_configs()
