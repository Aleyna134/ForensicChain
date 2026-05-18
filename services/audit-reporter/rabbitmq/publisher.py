import json
import uuid
from datetime import datetime, timezone
from typing import Any

import aio_pika


async def publish_event(
    exchange: aio_pika.abc.AbstractExchange,
    *,
    event_type: str,
    routing_key: str,
    artifact_id: str,
    case_id: str | None,
    actor_id: str,
    actor_role: str,
    corr_id: str,
    reason: str,
    payload: dict[str, Any],
) -> None:
    """
    Publish a domain event to the forensicchain.events topic exchange.

    Accepts a pre-opened exchange object — callers must not open new channels
    per publish call, as that would leak channels on the broker.
    """
    envelope = {
        "event_id": str(uuid.uuid4()),
        "event_type": event_type,
        "routing_key": routing_key,
        "artifact_id": artifact_id,
        "case_id": case_id,
        "actor_id": actor_id,
        "actor_role": actor_role,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "correlation_id": corr_id,
        "reason": reason,
        "payload": payload,
    }

    await exchange.publish(
        aio_pika.Message(
            body=json.dumps(envelope).encode(),
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            content_type="application/json",
        ),
        routing_key=routing_key,
    )
