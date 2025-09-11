import json
import logging
from django.core.management.base import BaseCommand
from kafka import KafkaConsumer
from django.conf import settings

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Consume Kafka events and print/log them"

    def add_arguments(self, parser):
        parser.add_argument(
            "--topic",
            type=str,
            default="margin-loan-events",
            help="Kafka topic to consume (default: margin-loan-events)",
        )
        parser.add_argument(
            "--group",
            type=str,
            default="oms-consumer-group",
            help="Consumer group ID",
        )

    def handle(self, *args, **options):
        topic = options["topic"]
        group_id = options["group"]

        logger.info(f"🔄 Starting Kafka consumer for topic={topic}, group={group_id}")

        consumer = KafkaConsumer(
            topic,
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            group_id=group_id,
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            key_deserializer=lambda k: k.decode("utf-8") if k else None,
            auto_offset_reset="earliest",  # start from earliest if no offset
            enable_auto_commit=True,
        )

        try:
            for msg in consumer:
                logger.info(
                    f"📥 Received event: topic={msg.topic}, "
                    f"partition={msg.partition}, offset={msg.offset}, "
                    f"key={msg.key}, value={msg.value}"
                )
                print(f"[Kafka] {msg.value}")  # also print to console
        except KeyboardInterrupt:
            logger.info("🛑 Kafka consumer stopped manually")
        finally:
            consumer.close()
            logger.info("✅ Kafka consumer closed")
