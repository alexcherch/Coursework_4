# Трекер привычек — backend

Backend-часть SPA для трекера полезных привычек (курсовой проект).

## Стек

- Python 3.14, Django 6.1, Django REST Framework
- PostgreSQL, Redis, Celery
- JWT-авторизация (`djangorestframework-simplejwt`)
- Документация API: drf-spectacular (Swagger UI)

## Установка

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.template .env   # и заполнить значения
```

Создание базы данных (пример):

```bash
psql -U postgres -c "CREATE ROLE coursework4 LOGIN PASSWORD 'coursework4';"
psql -U postgres -c "CREATE DATABASE coursework4 OWNER coursework4;"
```

## Запуск

```bash
redis-server                 # или: brew services start redis
python manage.py migrate
python manage.py runserver
```

Celery (в отдельных терминалах):

```bash
celery -A config worker -l info
celery -A config beat -l info
```

## Документация API

- Swagger UI: <http://localhost:8000/api/docs/>
- OpenAPI-схема: <http://localhost:8000/api/schema/>

## Проверки

```bash
pytest --cov=. --cov-report=term-missing
ruff check .
```
