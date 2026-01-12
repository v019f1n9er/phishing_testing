# phishing_testing


## Настройки безопасности
В проекте присутствуют значения по умолчанию, которые <ins>**необходимо изменить перед началом эксплуатации**</ins>, а именно:
- Файл `app.py` строка 26:
  ```
  app.secret_key = 'phishing-dashboard-2026-super-secret-key'
  ```
  значение параметра `app.secret_key` <ins>**настоятельно рекомендуется**</ins> изменить на своё

- Файл `app.py` строка 36:
  ```
  SESSION_COOKIE_SECURE=False
  ```
  по умолчанию `SESSION_COOKIE_SECURE=False`, но если вы используете HTTPS, то <ins>**настоятельно рекомендуется**</ins> сменить на `SESSION_COOKIE_SECURE=False`
  
- Файл `app.py` строки 94-95:
  ```
  'admin',
  generate_password_hash('passwd123'),
  ```
  `admin` и `passwd123` - данные пользователя, создаваемого по-умолчанию в БД, <ins>**настоятельно рекомендуется**</ins> изменить имя пользователя и пароль на уникальные


## Запуск в Docker-контейнере
Для того, чтобы запустить данный проект в Docker-контенере необходимо:
1. Клонировать репозиторий:
```
git clone https://github.com/v019f1n9er/phishing_testing.git
```
2. Собрать Docker-образ (<ins>предварительно установив Docker</ins>):
```
docker build -t phishing-dashboard .
```
4. Запустить контейнер:
```
docker run -d -p 8080:8080 --name phishing-dashboard-container phishing-dashboard
```
> `run -d` - запуск кнтейнера в фоновом режиме
> 
> `-p 8080:8080`  - открытие порта 8080 на хосте на порт 8080 в контейнере
> 
> `--name phishing-dashboard-container` - присвоение имени контейнеру
> 
> `phishing-dashboard` - имя образа, на основе которого создается контейнер
5. После этого приложение будет доступно по адресу: `http://ip_docker_container:8080`
  <img width="1606" height="488" alt="image" src="https://github.com/user-attachments/assets/c3fd679d-9572-44bf-9948-9720f4a6779e" />
6. После успешной авторизации можно будет увидеть основной интерфейс проекта:
  <img width="1606" height="488" alt="image" src="https://github.com/user-attachments/assets/db7e5bf5-13d4-4438-9698-3057770621b1" />





