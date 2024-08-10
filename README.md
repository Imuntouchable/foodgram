# Описание проекта
Проект foodgram предназначен для хранения и демонстрации другим пользователям рецептов. В нем можно публиковать, формировать и изменять какие либо рецепты. Также пользователь может создать профиль и подписываться на профили других пользователей.


## Инструкция по запуску проекта
```
git clone git@github.com:Imuntouchable/foodgram.git
cd infra/
sudo docker compose -f docker-compose.production.yml up -d
sudo docker compose -f docker-compose.production.yml exec backend python manage.py migrate
sudo docker compose -f docker-compose.production.yml exec backend python manage.py collectstatic
sudo docker compose -f docker-compose.production.yml exec backend cp -r /app/collected_static/. /backend_static/static/
```
## Примеры запросов к API
Пример запросов к API будут доступны после запуска проекта. Вы можете использовать инструменты для отправки HTTP-запросов, такие как Postman или curl, чтобы взаимодействовать с API проекта.
 
![image](https://github.com/user-attachments/assets/8df2a5d4-1928-4f51-9c4d-4d8314cce3b5)

## Используемые технологии:

Python
Django
Nginx
Docker
DockerHub
REST API
JavaScript
CSS
HTML

## Автор
Автор: Тогузов А. А.
