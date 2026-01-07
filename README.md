# phishing_testing

## Запуск в Docker-контейнере
Для того, чтобы запустить данный проект в Docker-контенере необходимо:
1. Клонировать репозиторий
`git clone https://github.com/v019f1n9er/phishing_testing.git`
2. Собрать Docker-образ
`docker build -t phishing-dashboard .`
3. Запустить контейнер 
`docker run -d -p 8080:8080 --name phishing-dashboard-container phishing-dashboard`
> `run -d` - запуск кнтейнера в фоновом режиме\n
> `-p 8080:8080`  - открытие порта 8080 на хосте на порт 8080 в контейнере\n
> `--name phishing-dashboard-container` - присвоение имени контейнеру\n
> `phishing-dashboard` - имя образа, на основе которого создается контейнер
4. После этого приложение будет доступно по адресу:
`http://ip_docker_container:8080`
<img width="1867" height="511" alt="image" src="https://github.com/user-attachments/assets/0c5b9a5b-91d2-410b-8917-8ab6f3c3a76d" />
