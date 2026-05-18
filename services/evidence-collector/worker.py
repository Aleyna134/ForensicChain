import os
import time
import json
import pika
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import text
from db.database import get_db, SessionLocal
from db.models import OutboxEvent
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("outbox-worker")

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", "5672"))
EXCHANGE_NAME = "forensicchain.events"
DLX_NAME = "forensicchain.dlx"
DLQ_NAME = "forensicchain.dlq"
MAX_RETRIES = 5

def get_rabbitmq_channel():
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(host=RABBITMQ_HOST, port=RABBITMQ_PORT)
    )
    channel = connection.channel()
    
    # Declare main exchange
    channel.exchange_declare(exchange=EXCHANGE_NAME, exchange_type='topic', durable=True)
    
    # Declare DLX and DLQ
    channel.exchange_declare(exchange=DLX_NAME, exchange_type='direct', durable=True)
    channel.queue_declare(queue=DLQ_NAME, durable=True)
    channel.queue_bind(exchange=DLX_NAME, queue=DLQ_NAME, routing_key='poison')
    
    channel.confirm_delivery()
    return connection, channel

def process_outbox():
    while True:
        try:
            # 1. Connect to RMQ
            connection, channel = get_rabbitmq_channel()
            logger.info("Connected to RabbitMQ with DLX configuration.")
            
            # 2. Polling loop
            while True:
                db = SessionLocal()
                try:
                    # Fetch batch of 10 with row-level locks
                    query = text("""
                        SELECT event_id FROM outbox_events 
                        WHERE status = 'PENDING' 
                        AND next_retry_at <= NOW()
                        ORDER BY created_at ASC 
                        LIMIT 10 
                        FOR UPDATE SKIP LOCKED
                    """)
                    
                    result = db.execute(query).fetchall()
                    if not result:
                        db.rollback()
                        db.close()
                        time.sleep(2)
                        continue
                        
                    event_ids = [row[0] for row in result]
                    events = db.query(OutboxEvent).filter(OutboxEvent.event_id.in_(event_ids)).all()
                    
                    for event in events:
                        payload = event.payload_json
                        routing_key = payload.get("routing_key") if isinstance(payload, dict) else event.event_type
                        
                        try:
                            # 3. Publish with Confirm
                            channel.basic_publish(
                                exchange=EXCHANGE_NAME,
                                routing_key=routing_key,
                                body=json.dumps(payload),
                                properties=pika.BasicProperties(
                                    delivery_mode=pika.spec.PERSISTENT_DELIVERY_MODE,
                                    message_id=str(event.event_id)
                                ),
                                mandatory=False
                            )
                            # Broker ACKed
                            event.status = 'PUBLISHED'
                            logger.info(f"Published event {event.event_id} ({event.event_type})")
                            
                        except pika.exceptions.AMQPError as e:
                            # Re-raise to trigger rollback and reconnect
                            logger.error(f"AMQP connection error during publish: {str(e)}")
                            raise
                            
                        except Exception as e:
                            logger.error(f"Publish failed for {event.event_id}: {str(e)}")
                            
                            event.retry_count += 1
                            event.last_error = str(e)
                            
                            if event.retry_count >= MAX_RETRIES:
                                # Poison message DLQ handling
                                poison_payload = {
                                    "original_payload": payload,
                                    "retry_count": event.retry_count,
                                    "last_error": event.last_error,
                                    "failed_at": datetime.now(timezone.utc).isoformat()
                                }
                                try:
                                    channel.basic_publish(
                                        exchange=DLX_NAME,
                                        routing_key='poison',
                                        body=json.dumps(poison_payload),
                                        properties=pika.BasicProperties(
                                            delivery_mode=pika.spec.PERSISTENT_DELIVERY_MODE,
                                            message_id=str(event.event_id)
                                        ),
                                        mandatory=False
                                    )
                                    event.status = 'FAILED'
                                    logger.warning(f"Sent event {event.event_id} to DLQ. Marked as FAILED.")
                                except pika.exceptions.AMQPError as dlx_err:
                                    logger.error(f"DLQ AMQP connection error: {str(dlx_err)}")
                                    raise
                                except Exception as dlx_err:
                                    logger.error(f"DLQ publish failed: {str(dlx_err)}")
                                    # Apply backoff to retry the DLQ publish later
                                    backoff_sec = min(2 ** event.retry_count, 300)
                                    event.next_retry_at = datetime.now(timezone.utc) + timedelta(seconds=backoff_sec)
                            else:
                                # Exponential backoff
                                backoff_sec = min(2 ** event.retry_count, 300)
                                event.next_retry_at = datetime.now(timezone.utc) + timedelta(seconds=backoff_sec)
                                logger.info(f"Scheduled retry for {event.event_id} in {backoff_sec}s")
                                
                    # 4. Commit transaction
                    db.commit()
                    
                except pika.exceptions.AMQPError as e:
                    db.rollback()
                    db.close()
                    logger.error(f"RabbitMQ connection lost: {str(e)}")
                    break # Break inner loop to reconnect
                except Exception as e:
                    db.rollback()
                    logger.error(f"Unexpected error processing outbox: {str(e)}")
                    time.sleep(2)
                finally:
                    if db:
                        db.close()
                        
        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ, retrying in 5s: {str(e)}")
            time.sleep(5)

if __name__ == "__main__":
    logger.info("Starting Outbox Publisher Worker...")
    # Wait for DB initialization / rabbitmq to be fully up
    time.sleep(10)
    process_outbox()
