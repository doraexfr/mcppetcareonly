# PetCare MCP Server

Масштабируемый MCP-сервер для платформы [PetCare](https://github.com/Petcare-X/petcare) — обеспечивает безопасный и стандартизированный доступ языковых моделей к данным о питомцах, ветеринарных клиниках и документах через протокол [Model Context Protocol](https://modelcontextprotocol.io).

---

## Содержание

- [Архитектура](#архитектура)
- [Стек технологий](#стек-технологий)
- [Быстрый старт](#быстрый-старт)
- [Переменные окружения](#переменные-окружения)
- [API и документация](#api-и-документация)
- [MCP-инструменты](#mcp-инструменты)
- [Безопасность](#безопасность)
- [Тесты](#тесты)
- [Структура проекта](#структура-проекта)

---

## Архитектура

Сервер построен по многоуровневому принципу с чётким разделением ответственности:

```
HTTP Request
    → JWT Middleware
    → TimeoutMiddleware (5 сек)
    → MCPRouter
    → ToolRegistry
    → Tool (pets / clinics / documents / assistant)
    → Service (бизнес-логика, OBAC-проверки)
    → Repository (SQL, asyncpg)
    → PostgreSQL / MinIO
```

Протокольный слой реализован через **FastMCP** (JSON-RPC 2.0 / SSE), что обеспечивает совместимость с любыми MCP-клиентами и языковыми моделями.

---

## Стек технологий

| Компонент | Технология |
|---|---|
| Фреймворк | FastAPI + Uvicorn |
| MCP-протокол | FastMCP (SSE / JSON-RPC 2.0) |
| База данных | PostgreSQL 15 + asyncpg + SQLAlchemy Core |
| Объектное хранилище | MinIO (S3-совместимое) + boto3 |
| Авторизация | JWT (PyJWT) |
| Очередь задач | Redis + Celery |
| LLM-адаптер | Gemma 4 через OpenRouter |
| Валидация | Pydantic v2 |
| Тесты | pytest + pytest-asyncio |
| Контейнеризация | Docker + Docker Compose |

---

## Быстрый старт

### Требования

- Docker и Docker Compose
- Python 3.11+

### Запуск через Docker Compose

```bash
# 1. Клонировать репозиторий
git clone https://github.com/doraexfr/mcppetcareonly.git
cd mcppetcareonly/mcp-server

# 2. Создать файл окружения
cp .env.docker.example .env.docker

# 3. Поднять весь стек
make up

# 4. Проверить что сервер запустился
curl http://localhost:8000/docs
```

Стек включает: **API** (порт 8000) + **PostgreSQL** (5432) + **MinIO** (9000, консоль 9001) + **Redis** (6379).

### Локальный запуск без Docker

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## Переменные окружения

Создай файл `.env.docker` в папке `mcp-server/`:

```env
APP_NAME=PetCare MCP API

# База данных
POSTGRES_URL=postgresql+asyncpg://petcare-admin:supersecret@postgres:5432/petcare

# MinIO
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=petcare
MINIO_SECRET_KEY=petcare123
MINIO_BUCKET_PRIVATE=petcare-private
MINIO_USE_SSL=false

# JWT
JWT_SECRET_KEY=change-this-in-production
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=60
AUTH_DEMO_PASSWORD=petcare-demo-password

# Таймауты
REQUEST_TIMEOUT_SECONDS=5

# LLM (Gemma 4 через OpenRouter)
DEFAULT_LLM=gemma
GEMMA_ENDPOINT=https://openrouter.ai/api/v1/chat/completions
GEMMA_API_KEY=your_openrouter_api_key
GEMMA_TIMEOUT_SECONDS=5
```

---

## API и документация

После запуска документация доступна по адресам:

| Интерфейс | URL |
|---|---|
| Swagger UI | http://localhost:8000/docs |
| ReDoc | http://localhost:8000/redoc |
| OpenAPI JSON | http://localhost:8000/openapi.json |

### Получить JWT-токен

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"user_id": "user-123", "password": "petcare-demo-password"}'
```

### Пример вызова инструмента

```bash
curl http://localhost:8000/mcp/pets/1/details \
  -H "Authorization: Bearer <your_token>"
```

---

## MCP-инструменты

### Питомцы (`pets`)

| Метод | Описание |
|---|---|
| `GET /mcp/pets/{pet_id}/details` | Полная карточка питомца (порода, возраст, антропометрия) |
| `GET /mcp/pets/{pet_id}/short` | Краткая сводка для списков |

### Клиники (`clinics`)

| Метод | Описание |
|---|---|
| `GET /mcp/clinics/city?vet_city=` | Поиск клиник по городу |
| `GET /mcp/clinics/location` | Поиск по геолокации (Haversine, радиус в км) |
| `POST /mcp/clinics/filter-available` | Фильтр по текущему времени работы |
| `GET /mcp/clinics/{vet_id}/contacts` | Телефон и сайт клиники |
| `GET /mcp/clinics/location-by-name` | Адрес и координаты по названию |

### Документы (`documents`)

| Метод | Описание |
|---|---|
| `GET /mcp/pets/{pet_id}/documents` | Список документов питомца |
| `GET /mcp/pets/{pet_id}/documents/by-date` | Фильтр по дате загрузки |
| `POST /mcp/documents/extract` | Извлечение текста из PDF/файла (MinIO) |

### Универсальный вызов

```bash
POST /mcp/execute
{
  "tool": "clinics",
  "method": "search_vet_clinics_by_city",
  "payload": {"vet_city": "Ростов-на-Дону"}
}
```

---

## Безопасность

- **JWT + OBAC** — каждый запрос проверяет совпадение `user_id` из токена с владельцем питомца в БД. При несовпадении возвращается `403 Forbidden`
- **Timeout Middleware** — жёсткий лимит 5 секунд на все запросы, возвращает `504` с кодом `TIMEOUT`
- **Типизированные ошибки** — единый формат ответа:

```json
{
  "data": null,
  "error": {
    "code": "FORBIDDEN",
    "message": "You do not own this pet"
  }
}
```

Коды ошибок: `NOT_FOUND` · `FORBIDDEN` · `VALIDATION_ERROR` · `TIMEOUT` · `INTERNAL_ERROR`

---

## Тесты

```bash
# Unit-тесты
make test

# Все тесты с coverage
make test-all
```

Покрытие ключевой бизнес-логики ≥ 75% (сервисы, роутер, middleware).

---

## Структура проекта

```
mcp-server/
├── app/
│   ├── api/            # HTTP-маршруты и middleware
│   ├── core/           # Конфигурация, исключения, безопасность
│   ├── common/         # Auth-зависимости
│   ├── mcp/            # ToolRegistry, MCPRouter, FastMCP-сервер
│   ├── tools/          # MCP-инструменты (pets, clinics, documents, assistant)
│   ├── services/       # Бизнес-логика
│   ├── repository/     # SQL-запросы (asyncpg)
│   ├── infrastructure/ # БД-сессия, S3-клиент
│   └── llm/            # LLM-адаптеры (Gemma, base, selector)
├── tests/
│   ├── unit/           # Юнит-тесты сервисов и роутера
│   └── integration/    # Интеграционные тесты с реальной БД и MinIO
├── docker/
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── init.sql        # Инициализация схемы БД
└── pyproject.toml
```

---

## Связь с основным проектом

Этот репозиторий — отдельный MCP-модуль платформы **PetCare**. Основной репозиторий платформы (фронтенд, Telegram-бот, REST API): [github.com/Petcare-X/petcare](https://github.com/Petcare-X/petcare)

Интеграция в основной бэкенд выполняется через монтирование подприложения FastAPI:

```python
from app.mcp.integration import mount_mcp_server
mount_mcp_server(app, mount_path="/mcp-server")
```
