import asyncio
import random
from datetime import datetime, timezone
import logging

import httpx
from faststream import FastStream
from faststream.rabbit import RabbitBroker
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config import settings
from src.database import AsyncSessionLocal
from src.messaging import PAYMENTS_QUEUE, ensure_rabbit_topology
from src.models import Payment


logger = logging.getLogger(__name__)
broker = RabbitBroker(settings.RABBITMQ_URL)
app = FastStream(broker)


@app.after_startup
async def setup_rabbit_topology():
    await ensure_rabbit_topology(broker)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True,
)
async def send_webhook(url: str, payload: dict):
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            url,
            json=payload,
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()


@broker.subscriber(PAYMENTS_QUEUE, retry=2)
async def process_payment(msg: dict):
    payment_id = msg.get("payment_id")
    if not payment_id:
        raise ValueError("Payment message is missing payment_id")

    async with AsyncSessionLocal() as db:
        payment = await db.get(Payment, payment_id)
        if payment is None:
            raise LookupError(f"Payment {payment_id} does not exist")

        if payment.status == "pending":
            await asyncio.sleep(random.uniform(2, 5))
            payment.status = (
                "succeeded" if random.random() < 0.9 else "failed"
            )
            payment.processed_at = datetime.now(timezone.utc)
            await db.commit()

        webhook_payload = {
            "payment_id": str(payment.id),
            "status": payment.status,
            "amount": float(payment.amount),
            "currency": payment.currency,
        }
        try:
            await send_webhook(payment.webhook_url, webhook_payload)
        except httpx.HTTPError:
            logger.exception("Webhook delivery failed for payment %s", payment_id)
            raise
