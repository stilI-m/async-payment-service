import asyncio
from typing import Annotated
from uuid import UUID

from fastapi import Depends, FastAPI, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.database import get_db
from src.models import OutboxEvent, Payment
from src.outbox_relay import outbox_worker
from src.schemas import PaymentCreate, PaymentResponse

app = FastAPI(title="Payment Processing API")


def verify_api_key(x_api_key: Annotated[str, Header()]):
    if x_api_key != settings.API_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API Key",
        )


@app.on_event("startup")
async def startup_event():
    asyncio.create_task(outbox_worker())


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
        return PaymentResponse(
            id=existing_payment.id,
            status=existing_payment.status,
            created_at=existing_payment.created_at.isoformat(),
        )

    new_payment = Payment(
        amount=payment_in.amount,
        currency=payment_in.currency,
        description=payment_in.description,
        metadata_=payment_in.metadata,
        idempotency_key=idempotency_key,
        webhook_url=str(payment_in.webhook_url),
    )
    db.add(new_payment)
    await db.flush()

    outbox_event = OutboxEvent(
        aggregate_id=str(new_payment.id),
        topic="payments.new",
        payload={"payment_id": str(new_payment.id)},
    )
    db.add(outbox_event)
    await db.commit()

    return PaymentResponse(
        id=new_payment.id,
        status=new_payment.status,
        created_at=new_payment.created_at.isoformat(),
    )


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
    return PaymentResponse(
        id=payment.id,
        status=payment.status,
        created_at=payment.created_at.isoformat(),
    )
