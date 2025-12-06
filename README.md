# Phishing Redirect Logger — README

Это подробная инструкция по запуску и использованию проекта phishing redirect logger (sec_multi.py), который:
- перенаправляет все HTTP-запросы на целевой сайт (TARGET_URL),
- логирует каждый переход в несколько форматов: SQLite (.db), CSV (.csv), TXT (.txt) и SQL-дамп (.sql),
- пригоден для локального запуска (Linux / macOS / Windows) и для запуска в Docker.

Файлы проекта (важные)
- sec_multi.py — основной сервер
- requirements_extra.txt — Python-зависимости
- Dockerfile_multi — Dockerfile для сборки контейнера
- data/ — директория для логов (logs.db, logs.csv, logs.txt, logs.sql)
- .dockerignore (рекомендуемое содержимое — ниже показана команда для его создания)

Содержание этого README:
- Переменные окружения и поведение по умолчанию
- Локальный запуск (dev)
- Запуск в Docker (docker build + docker run)
- Запуск через docker-compose
- Команды для Windows (PowerShell)
- Создание .dockerignore (команда)
- Тестирование и отладка (curl / docker logs / sqlite)
- Советы по безопасности и производительности
- Частые проблемы и решения

-------------------------
Переменные окружения (используются в sec_multi.py)
-------------------------
По умолчанию sec_multi.py использует следующие значения (если не заданы в окружении):

- TARGET_URL — URL для редиректа (по умолчанию: https://google.com)
- LOG_DB — путь к sqlite БД (по умолчанию: ./data/logs.db)
- LOG_CSV — путь к CSV файлу (по умолчанию: ./data/logs.csv)
- LOG_TXT — путь к TXT файлу (по умолчанию: ./data/logs.txt)
- LOG_SQL — путь к SQL дампу (по умолчанию: ./data/logs.sql)
- LISTEN_HOST — адрес прослушивания (по умолчанию: 0.0.0.0)
- LISTEN_PORT — порт (по умолчанию: 8080)

-------------------------
1) Локальный запуск (виртуальное окружение, для разработки / тестирования)
-------------------------
1. Клонируйте репозиторий и перейдите в папку проекта.

2. Создайте папку для логов:
- Linux / macOS:
  mkdir -p data
- Windows PowerShell:
  New-Item -ItemType Directory -Path .\data

3. Создайте и активируйте виртуальное окружение:
- Linux / macOS:
  python3 -m venv .venv
  source .venv/bin/activate
- Windows PowerShell:
  python -m venv .venv
  .\.venv\Scripts\Activate.ps1

4. Установите зависимости:
  pip install -r requirements_extra.txt

5. Установите переменные окружения (пример):
- Linux / macOS:
  export TARGET_URL="https://example.com"
  export LOG_DB="./data/logs.db"
  export LOG_CSV="./data/logs.csv"
  export LOG_TXT="./data/logs.txt"
  export LOG_SQL="./data/logs.sql"
- Windows PowerShell:
  $env:TARGET_URL="https://example.com"
  $env:LOG_DB=".\data\logs.db"
  $env:LOG_CSV=".\data\logs.csv"
  $env:LOG_TXT=".\data\logs.txt"
  $env:LOG_SQL=".\data\logs.sql"

6. Запустите:
- В режиме разработки (Flask built-in server):
  python sec_multi.py
- В режиме, более приближенном к продакшену, с gunicorn (установлен в requirements_extra.txt):
  gunicorn --bind 0.0.0.0:8080 --workers 2 sec_multi:app

7. Тест:
  curl -v "http://localhost:8080/some/path?x=1"
  — ожидается 302 Redirect на TARGET_URL/some/path?x=1

8. Проверьте папку data — должны появиться:
- logs.db
- logs.csv
- logs.txt
- logs.sql

-------------------------
2) Сборка и запуск в Docker
-------------------------
Перед запуском убедитесь, что в корне проекта есть:
- Dockerfile_multi
- requirements_extra.txt
- sec_multi.py
- папка data (локальная), которую вы будете монтировать в контейнер

2.1. Сборка образа:
- Из корня проекта выполните:
  docker build -t phishing-redirect-multi -f Dockerfile_multi .

2.2. Запуск контейнера (пример):
- Linux / macOS:
  docker run -d \
    --name phishing-redirect-multi \
    -p 8080:8080 \
    -e TARGET_URL="https://example.com" \
    -e LOG_DB="/data/logs.db" \
    -e LOG_CSV="/data/logs.csv" \
    -e LOG_TXT="/data/logs.txt" \
    -e LOG_SQL="/data/logs.sql" \
    -v "$(pwd)/data":/data \
    phishing-redirect-multi

- Windows PowerShell (пример):
  docker run -d `
    --name phishing-redirect-multi `
    -p 8080:8080 `
    -e TARGET_URL="https://example.com" `
    -e LOG_DB="C:\\data\\logs.db" `
    -e LOG_CSV="C:\\data\\logs.csv" `
    -e LOG_TXT="C:\\data\\logs.txt" `
    -e LOG_SQL="C:\\data\\logs.sql" `
    -v "${PWD}\\data":/data `
    phishing-redirect-multi

Пояснения:
- -v "$(pwd)/data":/data — монтирует локальную папку data в контейнер по пути /data (важно для сохранения логов и доступа к ним на хосте).
- Убедитесь, что Docker имеет доступ к этой папке (особенно на Windows: предоставьте права совместного доступа диска в Docker Desktop).

2.3. Проверка:
- Health:
  curl -v http://localhost:8080/health
  -> {"status":"ok"}

- Редирект:
  curl -v "http://localhost:8080/test?x=1"
  -> 302 Location: https://example.com/test?x=1

- Логи контейнера:
  docker logs -f phishing-redirect-multi

- Посмотреть файлы логов на хосте:
  ls -la ./data
  sqlite3 ./data/logs.db "SELECT id, timestamp, ip, path FROM visits ORDER BY id DESC LIMIT 10;"

-------------------------
3) docker-compose (рекомендуется для удобства)
-------------------------
Создайте файл `docker-compose.yml` (пример):

```yaml
version: "3.8"
services:
  phishing:
    build:
      context: .
      dockerfile: Dockerfile_multi
    image: phishing-redirect-multi
    container_name: phishing-redirect-multi
    ports:
      - "8080:8080"
    environment:
      - TARGET_URL=https://example.com
      - LOG_DB=/data/logs.db
      - LOG_CSV=/data/logs.csv
      - LOG_TXT=/data/logs.txt
      - LOG_SQL=/data/logs.sql
    volumes:
      - ./data:/data
    restart: unless-stopped
```

Запуск:
- docker-compose up -d --build
Остановка / удаление:
- docker-compose down

-------------------------
4) Создание .dockerignore — команда
-------------------------
Ниже показана команда (bash) для создания файла .dockerignore с типичными исключениями проекта:

Bash (Linux / macOS / WSL):
```bash
cat > .dockerignore <<'EOF'
__pycache__
*.pyc
*.pyo
*.pyd
env/
venv/
.git
.gitignore
*.db
*.sqlite
*.sql
EOF
```

PowerShell (Windows):
```powershell
@"
__pycache__
*.pyc
*.pyo
*.pyd
env/
venv/
.git
.gitignore
*.db
*.sqlite
*.sql
"@ > .dockerignore
```

-------------------------
5) Тестирование и отладка
-------------------------
- Проверка health:
  curl http://localhost:8080/health

- Проверка редиректа:
  curl -v "http://localhost:8080/some/path?x=1"  # должен вернуться 302 и Location

- Просмотр логов приложения (docker):
  docker logs -f phishing-redirect-multi

- Просмотр файлов логов на хосте:
  ls -la data
  head -n 20 data/logs.txt
  csvtool или Excel/LibreOffice для data/logs.csv

- Открыть SQLite:
  sqlite3 data/logs.db
  sqlite> .tables
  sqlite> SELECT * FROM visits ORDER BY id DESC LIMIT 5;

Если файлы не появляются:
- Убедитесь, что указали корректный путь при монтировании volume (полный абсолютный путь в Windows).
- Проверьте права доступа: на Linux может понадобиться chown/chmod:
  sudo chown -R $(id -u):$(id -g) ./data
- Проверьте логи контейнера для ошибок записи.
