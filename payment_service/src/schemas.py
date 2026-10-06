from decimal import Decimal
from datetime import datetime
from typing import Any, Dict, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl


class PaymentCreate(BaseModel):
    amount: Decimal = Field(..., gt=0)
    currency: str = Field(..., pattern="^(RUB|USD|EUR)$")
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    webhook_url: HttpUrl


class PaymentResponse(BaseModel):
    payment_id: UUID
    amount: Decimal
    currency: str
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    status: Literal["pending", "succeeded", "failed"]
    created_at: datetime
    processed_at: Optional[datetime] = None
