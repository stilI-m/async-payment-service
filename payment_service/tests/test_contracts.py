import unittest
from decimal import Decimal

from pydantic import ValidationError

from src.main import app
from src.models import Base, OutboxEvent, Payment
from src.schemas import PaymentCreate, PaymentResponse


class PaymentContractsTest(unittest.TestCase):
    def test_payment_schema_validates_supported_currencies(self):
        payment = PaymentCreate(
            amount=Decimal("1500.50"),
            currency="RUB",
            description="Оплата заказа",
            webhook_url="https://example.com/webhook",
        )
        self.assertEqual(payment.amount, Decimal("1500.50"))

        with self.assertRaises(ValidationError):
            PaymentCreate(
                amount=Decimal("1"),
                currency="GBP",
                webhook_url="https://example.com/webhook",
            )

    def test_payment_response_includes_details_and_payment_id(self):
        fields = PaymentResponse.model_fields
        self.assertIn("payment_id", fields)
        self.assertIn("amount", fields)
        self.assertIn("currency", fields)
        self.assertIn("metadata", fields)
        self.assertIn("processed_at", fields)

    def test_api_exposes_required_routes(self):
        routes = {
            route.path: route.methods for route in app.routes if hasattr(route, "path")
        }
        self.assertIn("/api/v1/payments", routes)
        self.assertIn("/api/v1/payments/{payment_id}", routes)
        self.assertIn("POST", routes["/api/v1/payments"])
        self.assertIn("GET", routes["/api/v1/payments/{payment_id}"])

    def test_models_create_expected_tables(self):
        tables = set(Base.metadata.tables)
        self.assertIn(Payment.__tablename__, tables)
        self.assertIn(OutboxEvent.__tablename__, tables)
        self.assertTrue(Payment.idempotency_key.unique)
        self.assertTrue(OutboxEvent.status.index)


if __name__ == "__main__":
    unittest.main()
