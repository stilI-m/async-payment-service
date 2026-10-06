from decimal import Decimal
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl


class PaymentCreate(BaseModel):
    amount: Decimal = Field(..., gt=0)
    currency: str = Field(..., pattern="^(RUB|USD|EUR)$")
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    webhook_url: HttpUrl


class PaymentResponse(BaseModel):
    id: UUID
    status: str
    created_at: str
