import asyncio
from contextlib import asynccontextmanager, suppress
from typing import Annotated
from uuid import UUID

from fastapi import Depends, FastAPI, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.database import engine, get_db
from src.models import OutboxEvent, Payment
from src.outbox_relay import outbox_worker
from src.schemas import PaymentCreate, PaymentResponse


def payment_response(payment: Payment) -> PaymentResponse:
    return PaymentResponse(
        payment_id=payment.id,
        amount=payment.amount,
        currency=payment.currency,
        description=payment.description,
        metadata=payment.metadata_,
        status=payment.status,
        created_at=payment.created_at,
        processed_at=payment.processed_at,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    relay_task = asyncio.create_task(outbox_worker())
    try:
        yield
    finally:
        relay_task.cancel()
        with suppress(asyncio.CancelledError):
            await relay_task
        await engine.dispose()


app = FastAPI(title="Payment Processing API", lifespan=lifespan)


def verify_api_key(x_api_key: Annotated[str, Header()]):
    if x_api_key != settings.API_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API Key",
        )


@app.get("/health", include_in_schema=False)
async def health_check():
    return {"status": "ok"}


@app.post(
    "/api/v1/payments",
    response_model=PaymentResponse,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(verify_api_key)],
)
async def create_payment(
    payment_in: PaymentCreate,
    idempotency_key: Annotated[str, Header(min_length=1)],
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Payment).where(Payment.idempotency_key == idempotency_key)
    existing_payment = (await db.execute(stmt)).scalar_one_or_none()
    if existing_payment:
        return payment_response(existing_payment)

    new_payment = Payment(
        amount=payment_in.amount,
        currency=payment_in.currency,
        description=payment_in.description,
        metadata_=payment_in.metadata,
        idempotency_key=idempotency_key,
        webhook_url=str(payment_in.webhook_url),
    )
    try:
        db.add(new_payment)
        await db.flush()

        outbox_event = OutboxEvent(
            aggregate_id=str(new_payment.id),
            topic="payments.new",
            payload={"payment_id": str(new_payment.id)},
        )
        db.add(outbox_event)
        await db.commit()
    except IntegrityError:
        await db.rollback()
        existing_payment = (await db.execute(stmt)).scalar_one_or_none()
        if existing_payment is None:
            raise
        return payment_response(existing_payment)

    return payment_response(new_payment)


@app.get(
    "/api/v1/payments/{payment_id}",
    dependencies=[Depends(verify_api_key)],
)
async def get_payment(payment_id: UUID, db: AsyncSession = Depends(get_db)):
    payment = await db.get(Payment, payment_id)
    if payment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found",
        )
    return payment_response(payment)
