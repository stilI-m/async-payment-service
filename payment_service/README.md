# Async Payment Service

An asynchronous payment-processing service built with FastAPI, PostgreSQL,
RabbitMQ, FastStream, SQLAlchemy, and Alembic.

## Run with Docker Compose

1. Optionally copy `.env.example` to `.env` and change `API_KEY` and service
   credentials. The example credentials are for local development only.
2. Start the services:

   ```powershell
   docker compose up --build --wait
   ```

   Compose waits for PostgreSQL, RabbitMQ, and the API health check. The API
   container applies Alembic migrations before starting.
3. The API is available at <http://localhost:8000>. RabbitMQ management is at
   <http://localhost:15672>.
4. Stop the services with `docker compose down`. Add `-v` only when you also
   want to remove the persisted local database and RabbitMQ data.

For local development outside Docker, start PostgreSQL and RabbitMQ using the
credentials in `.env.example`, copy that file to `.env`, then run:

```powershell
pip install -r requirements.txt
alembic upgrade head
uvicorn src.main:app --reload
```

In a second terminal, start the consumer:

```powershell
faststream run src.worker:app
```

## API

Every API endpoint requires the `X-API-Key` header. The POST endpoint also
requires an `Idempotency-Key` header.

Create a payment:

```powershell
curl.exe -X POST http://localhost:8000/api/v1/payments `
  -H "X-API-Key: secret_test_key" `
  -H "Idempotency-Key: order-123" `
  -H "Content-Type: application/json" `
  -d '{"amount":"1500.50","currency":"RUB","description":"Order 123","metadata":{"order_id":"123"},"webhook_url":"https://example.com/webhooks/payment"}'
```

The API returns `202 Accepted` with `payment_id`, payment details, status, and
creation time. Fetch the current payment state with:

```powershell
curl.exe http://localhost:8000/api/v1/payments/<payment_id> `
  -H "X-API-Key: secret_test_key"
```

The consumer emulates payment processing with a 2–5 second delay and a 90%
success rate. It retries webhook delivery three times with exponential backoff.
Failed message processing is retried by RabbitMQ consumer handling and rejected
messages are routed to the durable `payments.dlq` queue.

## Architecture

- Payment creation and its outbox event are saved in one database transaction.
- The API's outbox relay publishes pending events to RabbitMQ and retries after
  connection or publishing failures.
- The consumer updates the payment state and sends a webhook. Processing is
  idempotent across message redelivery; webhook failures are retried.
- PostgreSQL and RabbitMQ data are persisted in named Compose volumes.
