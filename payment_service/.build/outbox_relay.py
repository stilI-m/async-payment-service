import asyncio

from faststream.rabbit import RabbitBroker
from sqlalchemy import select

from src.config import settings
from src.database import AsyncSessionLocal
from src.models import OutboxEvent


async def outbox_worker():
    """Publish pending outbox events and mark them processed."""
    broker = RabbitBroker(settings.RABBITMQ_URL)
    await broker.connect()

    try:
        while True:
            async with AsyncSessionLocal() as db:
                stmt = (
                    select(OutboxEvent).where(OutboxEvent.status == "pending").limit(50)
                )
                result = await db.execute(stmt)
                events = result.scalars().all()

                for event in events:
                    await broker.publish(event.payload, queue=event.topic)
                    event.status = "processed"

                if events:
                    await db.commit()

            await asyncio.sleep(2)
    finally:
        await broker.close()
