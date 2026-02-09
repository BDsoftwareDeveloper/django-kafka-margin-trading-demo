
import json
import logging
from kafka import KafkaProducer
from django.conf import settings
from core.models import AuditLog, Client, MarginLoan

logger = logging.getLogger(__name__)


class KafkaProducerWrapper:
    """Singleton Kafka Producer Wrapper"""

    _producer = None

    @classmethod
    def get_producer(cls):
        if cls._producer is None:
            try:
                cls._producer = KafkaProducer(
                    bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
                    value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                    key_serializer=lambda k: str(k).encode("utf-8") if k else None,
                    acks="all",  # ✅ safer delivery
                    retries=3,   # ✅ auto retry
                )
                logger.info("✅ Kafka Producer initialized")
            except Exception as e:
                logger.error(f"❌ Failed to initialize Kafka Producer: {e}")
                raise
        return cls._producer

    @classmethod
    def send_event(cls, topic: str, key: str, event: dict, client=None, loan=None):
        """Send event to Kafka and log to AuditLog"""
        try:
            producer = cls.get_producer()
            future = producer.send(topic, key=key, value=event)
            result = future.get(timeout=10)  # wait for ack

            logger.info(
                f"📤 Sent event to {topic} | partition={result.partition} offset={result.offset}"
            )

            # ✅ Also log the event into AuditLog
            AuditLog.log_event(
                event_type=event.get("type"),
                client=client,
                loan=loan,
                details=event,
            )

            return True
        except Exception as e:
            logger.error(f"❌ Kafka send_event error: {e} | topic={topic} | event={event}")
            return False

    @classmethod
    def close(cls):
        if cls._producer:
            try:
                cls._producer.flush()
                cls._producer.close()
                logger.info("🛑 Kafka Producer closed")
            except Exception as e:
                logger.warning(f"⚠️ Error closing Kafka Producer: {e}")
            finally:
                cls._producer = None


# Example event helpers
def publish_margin_request(client_id: int, amount: float, loan: MarginLoan = None):
    event = {
        "type": "MARGIN_REQUEST",
        "client_id": client_id,
        "amount": amount,
    }
    client = Client.objects.filter(id=client_id).first()
    # Change from margin-loan-events to margin_requests
    return KafkaProducerWrapper.send_event(
        "margin-loan-events", key=str(client_id), event=event, client=client, loan=loan
    )

def publish_forced_sell(client_id: int, portfolio_id: int, reason: str):
    event = {
        "type": "FORCED_SELL",
        "client_id": client_id,
        "portfolio_id": portfolio_id,
        "reason": reason,
    }
    client = Client.objects.filter(id=client_id).first()
    # Change from portfolio-events to portfolio_events
    return KafkaProducerWrapper.send_event(
        "portfolio-events", key=str(client_id), event=event, client=client
    )