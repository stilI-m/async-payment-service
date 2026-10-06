import asyncio
import logging

from faststream.rabbit import RabbitBroker
from sqlalchemy import select

from src.config import settings
from src.database import AsyncSessionLocal
from src.messaging import ensure_rabbit_topology
from src.models import OutboxEvent


logger = logging.getLogger(__name__)


async def outbox_worker():
    """Publish pending outbox events and mark them processed."""
    while True:
        broker = RabbitBroker(settings.RABBITMQ_URL)
        try:
            await broker.connect()
            await ensure_rabbit_topology(broker)

            while True:
                async with AsyncSessionLocal() as db:
                    stmt = (
                        select(OutboxEvent)
                        .where(OutboxEvent.status == "pending")
                        .order_by(OutboxEvent.created_at)
                        .limit(50)
                        .with_for_update(skip_locked=True)
                    )
                    result = await db.execute(stmt)
                    events = result.scalars().all()

                    for event in events:
                        await broker.publish(event.payload, queue=event.topic)
                        event.status = "processed"

                    if events:
                        await db.commit()

                await asyncio.sleep(2)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Outbox relay failed; retrying in 2 seconds")
            await asyncio.sleep(2)
        finally:
            try:
                await broker.close()
            except Exception:
                logger.exception("Failed to close the outbox RabbitMQ connection")
