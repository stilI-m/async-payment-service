from faststream.rabbit import RabbitBroker, RabbitExchange, RabbitQueue


DEAD_LETTER_EXCHANGE = RabbitExchange("payments.dlx", durable=True)
DEAD_LETTER_QUEUE = RabbitQueue("payments.dlq", durable=True)
PAYMENTS_QUEUE = RabbitQueue(
    "payments.new",
    durable=True,
    arguments={
        "x-dead-letter-exchange": DEAD_LETTER_EXCHANGE.name,
        "x-dead-letter-routing-key": DEAD_LETTER_QUEUE.name,
    },
)


async def ensure_rabbit_topology(broker: RabbitBroker) -> None:
    dead_letter_exchange = await broker.declare_exchange(DEAD_LETTER_EXCHANGE)
    await broker.declare_queue(PAYMENTS_QUEUE)
    dead_letter_queue = await broker.declare_queue(DEAD_LETTER_QUEUE)
    await dead_letter_queue.bind(
        dead_letter_exchange,
        routing_key=DEAD_LETTER_QUEUE.name,
    )
