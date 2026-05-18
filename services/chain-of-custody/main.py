import asyncio
import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import aio_pika
from fastapi import FastAPI

from consumer import consume_events
from db.database import Base, engine
from routers.custody import router as custody_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger(__name__)

RABBITMQ_URL: str = os.environ["RABBITMQ_URL"]
_EXCHANGE_NAME: str = "forensicchain.events"
_DLX_NAME: str = "forensicchain.dlx"
_QUEUE_NAME: str = "custody.events.queue"
_DLQ_NAME: str = "custody.events.dlq"


async def _setup_rabbitmq(connection: aio_pika.abc.AbstractConnection) -> None:
    """
    Declare exchanges, queues, and bindings idempotently on startup.
    Running this every boot is safe — all declarations use durable=True
    and will no-op if the topology already exists.
    """
    channel = await connection.channel()

    dlx = await channel.declare_exchange(
        _DLX_NAME,
        type=aio_pika.ExchangeType.DIRECT,
        durable=True,
    )
    dlq = await channel.declare_queue(_DLQ_NAME, durable=True)
    await dlq.bind(dlx, routing_key=_DLQ_NAME)

    exchange = await channel.declare_exchange(
        _EXCHANGE_NAME,
        type=aio_pika.ExchangeType.TOPIC,
        durable=True,
    )
    queue = await channel.declare_queue(
        _QUEUE_NAME,
        durable=True,
        arguments={
            "x-dead-letter-exchange": _DLX_NAME,
            "x-dead-letter-routing-key": _DLQ_NAME,
        },
    )
    await queue.bind(exchange, routing_key="forensicchain.#")

    logger.info("RabbitMQ topology ready")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables ensured")

    connection = await aio_pika.connect_robust(RABBITMQ_URL)
    await _setup_rabbitmq(connection)

    consumer_task = asyncio.create_task(consume_events(connection))
    logger.info("RabbitMQ consumer started")

    yield

    consumer_task.cancel()
    try:
        await consumer_task
    except asyncio.CancelledError:
        pass
    await connection.close()
    logger.info("RabbitMQ connection closed")


app = FastAPI(title="ForensicChain — Chain of Custody", lifespan=lifespan)
app.include_router(custody_router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "chain-of-custody"}
