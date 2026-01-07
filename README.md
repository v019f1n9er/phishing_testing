# phishing_testing

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
4. После этого приложение будет доступно по адресу:
`http://ip_docker_container:8080`
<img width="1606" height="488" alt="image" src="https://github.com/user-attachments/assets/db7e5bf5-13d4-4438-9698-3057770621b1" />
