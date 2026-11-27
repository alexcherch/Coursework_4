# Трекер привычек — backend

Backend-часть SPA для трекера полезных привычек. Реализованы регистрация и JWT-авторизация, CRUD привычек,
публичные привычки, пагинация, отметка выполнения и напоминания в Telegram
по расписанию через Celery.

## Возможности

- Регистрация и авторизация по email (JWT: access + refresh).
- CRUD привычек: пользователь видит и меняет только свои привычки.
- Публичные привычки — доступны всем авторизованным пользователям только для чтения.
- Пагинация `limit`/`offset`, по 5 привычек на страницу по умолчанию.
- Валидация бизнес-правил привычек (см. раздел «Правила привычек»).
- Отметка выполнения привычки на текущую дату (одна запись в день).
- Напоминания в Telegram по расписанию: Celery Beat каждую минуту запускает
  диспетчер, Celery Worker отправляет сообщения.
- Документация API: Swagger UI и OpenAPI-схема.

## Стек

| Компонент | Технология |
|---|---|
| Язык | Python 3.14 |
| Web | Django 6.1, Django REST Framework 3.18 |
| БД | PostgreSQL |
| Очереди | Celery 5.7 + Redis |
| Авторизация | djangorestframework-simplejwt |
| Документация | drf-spectacular |
| Тесты | pytest, pytest-django, pytest-cov |
| Линтер | ruff |

## Структура проекта

```
config/          настройки, urls, celery
users/           кастомный User (email + telegram_id), регистрация, JWT
habits/          Habit, HabitCompletion, валидаторы, CRUD, пагинация
notifications/   Telegram-клиент и Celery-задачи
```

## Установка

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.template .env
```

Заполни `.env` (см. таблицу переменных ниже). Создание базы данных:

```bash
psql -U postgres -c "CREATE ROLE coursework4 LOGIN PASSWORD 'coursework4' CREATEDB;"
psql -U postgres -c "CREATE DATABASE coursework4 OWNER coursework4;"
```

Примени миграции и создай администратора:

```bash
python manage.py migrate
python manage.py createsuperuser
```

## Переменные окружения

| Переменная | Назначение |
|---|---|
| `SECRET_KEY` | секретный ключ Django (обязателен) |
| `DEBUG` | режим отладки (`True`/`False`) |
| `ALLOWED_HOSTS` | список хостов через запятую |
| `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` | подключение к PostgreSQL |
| `CELERY_BROKER_URL` | брокер Celery (Redis, например `redis://localhost:6379/0`) |
| `CELERY_RESULT_BACKEND` | backend результатов (`redis://localhost:6379/1`) |
| `TELEGRAM_BOT_TOKEN` | токен бота от @BotFather |
| `CORS_ALLOWED_ORIGINS` | origins фронтенда через запятую |

Шаблон со всеми переменными — `.env.template`.

## Запуск

```bash
redis-server                 # или: brew services start redis
python manage.py runserver
```

Celery (в отдельных терминалах):

```bash
celery -A config worker -l info
celery -A config beat -l info
```

## Telegram

1. Создай бота у **@BotFather** (`/newbot`) и получи токен.
2. Пропиши токен в `.env` → `TELEGRAM_BOT_TOKEN`.
3. Нажми **Start** в чате с ботом (бот не может писать первым).
4. Узнай `chat_id`: `https://api.telegram.org/bot<TOKEN>/getUpdates`.
5. Сохрани `chat_id` в профиле пользователя (`telegram_id`) — через API, админку
   или shell:

```bash
python manage.py shell -c "from users.models import User; u=User.objects.get(email='user@example.com'); u.telegram_id=<CHAT_ID>; u.save()"
```

Проверка отправки без Celery:

```bash
python manage.py shell -c "from notifications.telegram import send_message; print(send_message(<CHAT_ID>, 'Тест'))"
```

Дальше Beat раз в минуту запускает `dispatch_habit_reminders`: выбирает полезные
привычки, время которых совпало с текущей минутой и у которых подошёл срок по
`periodicity`, и ставит в очередь `send_habit_reminder`. При успешной отправке
обновляется `last_reminded_at`.

## API

Базовый URL: `/api/`. Для защищённых эндпоинтов нужен заголовок
`Authorization: Bearer <access>`.

| Метод | URL | Доступ | Описание |
|---|---|---|---|
| POST | `/api/users/register/` | без авторизации | регистрация |
| POST | `/api/users/token/` | без авторизации | получить access + refresh |
| POST | `/api/users/token/refresh/` | без авторизации | обновить access |
| GET | `/api/habits/` | только свои | список привычек (пагинация) |
| POST | `/api/habits/` | авторизован | создать привычку |
| GET | `/api/habits/{id}/` | только свои | получить привычку |
| PUT/PATCH | `/api/habits/{id}/` | только свои | изменить привычку |
| DELETE | `/api/habits/{id}/` | только свои | удалить привычку |
| GET | `/api/habits/public/` | авторизован | публичные привычки (read-only) |
| POST | `/api/habits/{id}/complete/` | только свои | отметить выполнение на сегодня |

Чужие привычки недоступны: возвращается `404`.

**Пагинация:** `?limit=5&offset=0`; ответ содержит `count`, `next`, `previous`,
`results`. По умолчанию 5 записей на страницу.

**Отметка выполнения:** первый вызов за день возвращает `201`, повторный — `200`
(запись не дублируется).

### Правила привычек

- нельзя одновременно указать `reward` и `linked_habit`;
- `duration` — от 1 до 120 секунд;
- `linked_habit` — только приятная привычка того же пользователя;
- у приятной привычки (`is_pleasant=true`) нет `reward` и `linked_habit`;
- `periodicity` — от 1 до 7 дней;
- привычку нельзя связать с самой собой.

## Документация

- Swagger UI: <http://localhost:8000/api/docs/>
- OpenAPI-схема: <http://localhost:8000/api/schema/>

## Тесты и покрытие

```bash
pytest --cov=. --cov-report=term-missing
```

Порог покрытия — 80% (`fail_under` в `pyproject.toml`); миграции, тесты и
служебные файлы в расчёт не входят.

## Качество кода

```bash
ruff check .
```

Настройки линтера — в `pyproject.toml` (PEP 8).

## Пример запроса

```bash
curl -X POST http://localhost:8000/api/users/register/ \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "StrongPass123"}'

curl -X POST http://localhost:8000/api/habits/ \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"place": "Дом", "time": "09:00", "action": "Зарядка", "duration": 60, "reward": "Кофе"}'
```
