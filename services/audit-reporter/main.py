import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import aio_pika
from fastapi import FastAPI

from db.database import Base, engine
from routers.reports import router as reports_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger(__name__)

RABBITMQ_URL: str = os.environ["RABBITMQ_URL"]
_EXCHANGE_NAME: str = "forensicchain.events"


async def _setup_rabbitmq(
    connection: aio_pika.abc.AbstractConnection,
) -> tuple[aio_pika.abc.AbstractChannel, aio_pika.abc.AbstractExchange]:
    channel = await connection.channel()
    exchange = await channel.declare_exchange(
        _EXCHANGE_NAME,
        type=aio_pika.ExchangeType.TOPIC,
        durable=True,
    )
    logger.info("RabbitMQ exchange ready: %s", _EXCHANGE_NAME)
    return channel, exchange


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables ensured")

    connection = await aio_pika.connect_robust(RABBITMQ_URL)
    _, exchange = await _setup_rabbitmq(connection)

    app.state.rabbitmq_connection = connection
    app.state.rabbitmq_exchange = exchange
    logger.info("RabbitMQ connection established")

    yield

    await connection.close()
    logger.info("RabbitMQ connection closed")


app = FastAPI(title="ForensicChain — Audit Reporter", lifespan=lifespan)
app.include_router(reports_router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "audit-reporter"}
