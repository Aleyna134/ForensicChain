import asyncio
import json
import logging
import os
from datetime import datetime, timezone

import aio_pika
from sqlalchemy import text
from sqlalchemy.orm import Session

from db.database import SessionLocal
from db.models import OutboxEvent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("outbox-worker")

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/")
EXCHANGE_NAME = "forensicchain.events"
MAX_RETRIES = 5


async def publish_outbox_events(exchange: aio_pika.abc.AbstractExchange) -> None:
    """
    Poll outbox_events where published=False, publish to RabbitMQ, mark as published.
    On repeated failure the event stays unpublished with last_error set; the spec's
    retry/DLQ mechanism is handled by the chain-of-custody consumer, not here.
    """
    db: Session = SessionLocal()
    try:
        result = db.execute(text("""
            SELECT id FROM outbox_events
            WHERE published = FALSE
            ORDER BY created_at ASC
            LIMIT 10
            FOR UPDATE SKIP LOCKED
        """)).fetchall()

        if not result:
            db.rollback()
            return

        row_ids = [row[0] for row in result]
        events = db.query(OutboxEvent).filter(OutboxEvent.id.in_(row_ids)).all()

        for event in events:
            try:
                await exchange.publish(
                    aio_pika.Message(
                        body=json.dumps(event.payload).encode(),
                        delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                        content_type="application/json",
                        message_id=str(event.event_id),
                    ),
                    routing_key=event.routing_key,
                )
                event.published = True
                event.published_at = datetime.now(timezone.utc)
                logger.info("Published event %s (%s)", event.event_id, event.event_type)

            except Exception as e:
                event.retry_count += 1
                event.last_error = str(e)
                if event.retry_count >= MAX_RETRIES:
                    logger.error(
                        "Giving up on event %s after %d attempts: %s",
                        event.event_id, event.retry_count, e,
                    )
                else:
                    logger.error(
                        "Publish failed for %s (attempt %d): %s",
                        event.event_id, event.retry_count, e,
                    )

        db.commit()

    except Exception as e:
        db.rollback()
        logger.error("Unexpected error in publish cycle: %s", e)
    finally:
        db.close()


async def main() -> None:
    await asyncio.sleep(10)  # allow DB + RabbitMQ to be fully ready

    logger.info("Outbox worker starting, connecting to %s...", RABBITMQ_URL)

    # connect_robust: automatically reconnects on transient network failures
    connection = await aio_pika.connect_robust(RABBITMQ_URL)

    async with connection:
        channel = await connection.channel()

        exchange = await channel.declare_exchange(
            EXCHANGE_NAME, aio_pika.ExchangeType.TOPIC, durable=True
        )

        logger.info("Outbox worker ready. Polling every 2s.")

        while True:
            await publish_outbox_events(exchange)
            await asyncio.sleep(2)


if __name__ == "__main__":
    asyncio.run(main())
