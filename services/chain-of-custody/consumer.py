import asyncio
import json
import logging
from datetime import datetime

import aio_pika
from aio_pika.abc import AbstractIncomingMessage
from sqlalchemy.ext.asyncio import AsyncSession

from chain.custody_chain import build_event_content, compute_event_hash
from db.database import AsyncSessionLocal
from db.repository import (
    get_last_event_hash,
    insert_custody_event,
    is_already_processed,
    mark_processed,
)

logger = logging.getLogger(__name__)

_MAX_RETRIES: int = 3
_EXCHANGE_NAME: str = "forensicchain.events"
_QUEUE_NAME: str = "custody.events.queue"


async def _process_message(message: AbstractIncomingMessage, db: AsyncSession) -> None:
    """
    Parse and persist a single custody event from the RabbitMQ message body.

    Raises on any processing failure so the caller can apply retry logic.
    The caller is responsible for ack/nack — this function does not touch
    message acknowledgement.
    """
    body: dict = json.loads(message.body)

    event_id: str = body["event_id"]
    artifact_id: str = body["artifact_id"]

    if await is_already_processed(db, event_id):
        logger.info("duplicate event %s — skipping", event_id)
        return

    previous_hash: str | None = await get_last_event_hash(db, artifact_id)

    event_content = build_event_content(
        event_id=event_id,
        event_type=body["event_type"],
        artifact_id=artifact_id,
        case_id=body.get("case_id"),
        actor_id=body["actor_id"],
        actor_role=body["actor_role"],
        timestamp=body["timestamp"],
        reason=body.get("reason"),
        ip_address=body.get("payload", {}).get("ip_address"),
        correlation_id=body.get("correlation_id"),
        payload=body.get("payload", {}),
        previous_event_hash=previous_hash,
    )
    event_hash = compute_event_hash(event_content)

    timestamp = datetime.fromisoformat(body["timestamp"].replace("Z", "+00:00"))

    await insert_custody_event(
        db,
        event_id=event_id,
        artifact_id=artifact_id,
        case_id=body.get("case_id"),
        actor_id=body["actor_id"],
        actor_role=body["actor_role"],
        event_type=body["event_type"],
        timestamp=timestamp,
        reason=body.get("reason"),
        ip_address=body.get("payload", {}).get("ip_address"),
        correlation_id=body.get("correlation_id"),
        payload=body.get("payload", {}),
        previous_event_hash=previous_hash,
        event_hash=event_hash,
    )
    await mark_processed(db, event_id)
    await db.commit()

    logger.info(
        "custody event persisted: event_id=%s artifact_id=%s type=%s",
        event_id, artifact_id, body["event_type"],
    )


async def consume_events(connection: aio_pika.abc.AbstractConnection) -> None:
    """
    Long-running coroutine: consumes custody events from RabbitMQ.

    Retry strategy (plan §3):
      • x-retry-count starts at 0 on first delivery.
      • On failure: if retry_count < _MAX_RETRIES, publish a retry copy with
        x-retry-count + 1 to the main topic exchange (same routing key), then
        ack the original so it is consumed exactly once.
      • After _MAX_RETRIES failures, reject with requeue=False so RabbitMQ
        routes the message to the DLX / DLQ.
      • Total attempts before DLQ: 1 initial + _MAX_RETRIES retries = 4.
    """
    channel = await connection.channel()
    await channel.set_qos(prefetch_count=10)

    exchange = await channel.get_exchange(_EXCHANGE_NAME)
    queue = await channel.get_queue(_QUEUE_NAME)

    async with queue.iterator() as q:
        async for message in q:
            retry_count: int = int((message.headers or {}).get("x-retry-count", 0))

            try:
                async with AsyncSessionLocal() as db:
                    await _process_message(message, db)

                await message.ack()

            except Exception as exc:
                logger.error(
                    "failed to process event (retry_count=%d): %s", retry_count, exc, exc_info=True
                )

                if retry_count < _MAX_RETRIES:
                    new_headers = dict(message.headers or {})
                    new_headers["x-retry-count"] = retry_count + 1

                    await exchange.publish(
                        aio_pika.Message(
                            body=message.body,
                            headers=new_headers,
                            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                            content_type="application/json",
                        ),
                        routing_key=message.routing_key,
                    )
                    await message.ack()
                    logger.warning(
                        "requeued event with retry_count=%d routing_key=%s",
                        retry_count + 1, message.routing_key,
                    )
                else:
                    await message.reject(requeue=False)
                    logger.error(
                        "event exhausted %d retries — sent to DLQ: routing_key=%s",
                        _MAX_RETRIES, message.routing_key,
                    )
