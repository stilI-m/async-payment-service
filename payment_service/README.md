# Asynchronous Payment Processing Service

Микросервис для асинхронной обработки платежей.

## Стек технологий
- FastAPI + Pydantic v2
- SQLAlchemy 2.0 (asyncpg) + PostgreSQL
- RabbitMQ + FastStream
- Docker Compose

## Архитектурные паттерны
- **Transactional Outbox**: Гарантированная публикация событий в брокер (сохранение в БД + фоновый релей).
- **Idempotency Key**: Защита от дублей на уровне API (через заголовок).
- **Retry Pattern**: Экспоненциальные повторные попытки при отправке webhook (используется `tenacity`).
- **Dead Letter Queue (DLQ)**: Сообщения падают в `payments.dlq` после 3 неудачных попыток обработки (настроено через x-arguments RabbitMQ).

## Запуск
```bash
docker-compose up --build