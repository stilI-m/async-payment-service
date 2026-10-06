import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Numeric, DateTime, Enum, JSON
from sqlalchemy.dialects.postgresql import UUID, JSONB
from src.database import Base

class Payment(Base):
    __tablename__ = "payments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), nullable=False)
    description = Column(String, nullable=True)
    metadata_ = Column("metadata", JSONB, nullable=True)
    status = Column(Enum("pending", "succeeded", "failed", name="payment_status"), default="pending")
    idempotency_key = Column(String, unique=True, nullable=False, index=True)
    webhook_url = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    processed_at = Column(DateTime(timezone=True), nullable=True)

class OutboxEvent(Base):
    __tablename__ = "outbox_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    aggregate_id = Column(String, nullable=False) # ID платежа
    topic = Column(String, nullable=False)
    payload = Column(JSON, nullable=False)
    status = Column(Enum("pending", "processed", name="outbox_status"), default="pending", index=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))