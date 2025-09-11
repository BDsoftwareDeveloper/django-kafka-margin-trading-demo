# import os
# import django
# import json
# import logging
# from kafka import KafkaConsumer
# from django.utils import timezone
# from django.core.exceptions import ObjectDoesNotExist
# from django.conf import settings
# os.environ.setdefault("DJANGO_SETTINGS_MODULE", "oms_margin_demo.settings")
# django.setup()
# from core.models import AuditLog  # ✅ import after django.setup()


# logger = logging.getLogger(__name__)

# def safe_deserializer(m):
#     try:
#         if not m:
#             return None
#         return json.loads(m.decode("utf-8"))
#     except Exception as e:
#         logger.error(f"⚠️ Failed to deserialize Kafka message: {e} | raw={m}")
#         return None
    
    
# def start_consumer(topic: str, group_id: str, handler):
#     """Generic Kafka consumer runner"""
#     consumer = KafkaConsumer(
#         topic,
#         bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
#         auto_offset_reset="earliest",
#         enable_auto_commit=True,
#         group_id=group_id,
#         value_deserializer=safe_deserializer,  # ✅ now returns dict
#     )

#     logger.info(f"📥 Consumer started for topic={topic}, group={group_id}")

#     for message in consumer:
#         event = message.value
#         if not event:   # ✅ skip invalid/empty messages
#             logger.warning("⚠️ Skipping empty or invalid Kafka event")
#             continue

#         print("📩 Received Portfolio Event:", event)
#         save_audit_log(event)

# def save_audit_log(event, client=None, loan=None):
#     try:
#         if not isinstance(event, dict):
#             logger.warning(f"⚠️ Ignoring non-dict event: {event}")
#             return

#         AuditLog.objects.create(
#             event_type=event.get("type"),
#             client=client,
#             loan=loan,
#             details=event,
#         )
#         logger.info(f"📝 AuditLog saved: {event}")
#     except Exception as e:
#         logger.error(f"❌ Failed to save AuditLog: {e} | event={event}")


# # Handlers
# def handle_portfolio_event(event: dict):
#     if event.get("type") == "FORCED_SELL":
#         logger.warning(f"⚠️ Forced Sell triggered: {event}")
#         # TODO: Update DB, Portfolio, MarginLoan etc.


# def handle_margin_event(event: dict):
#     if event.get("type") == "MARGIN_REQUEST":
#         logger.info(f"💰 Margin Request received: {event}")
#         # TODO: Business logic for margin approval/rejection




# # Dispatcher entrypoint
# if __name__ == "__main__":
#     import sys

#     consumer_type = sys.argv[1] if len(sys.argv) > 1 else "portfolio"

#     if consumer_type == "portfolio":
#         start_consumer("portfolio-events", "oms-portfolio-group", handle_portfolio_event)
#     elif consumer_type == "margin":
#         start_consumer("margin-loan-events", "oms-margin-group", handle_margin_event)
#     else:
#         print("❌ Unknown consumer type. Use: portfolio | margin")



import os
import django
import json
import logging
import time
from kafka import KafkaConsumer, KafkaProducer
from kafka.errors import NoBrokersAvailable, KafkaError
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings

# Setup Django first
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "oms_margin_demo.settings")
django.setup()

from core.models import AuditLog, Client, MarginLoan

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def safe_deserializer(m):
    """Safely deserialize Kafka message"""
    try:
        if not m:
            return None
        return json.loads(m.decode("utf-8"))
    except Exception as e:
        logger.error(f"⚠️ Failed to deserialize Kafka message: {e} | raw={m}")
        return None

def save_audit_log(event, client_id=None, loan_id=None):
    """Save audit log with proper error handling"""
    try:
        if not isinstance(event, dict):
            logger.warning(f"⚠️ Ignoring non-dict event: {event}")
            return False

        # Get client and loan objects if IDs are provided
        client = None
        loan = None
        
        if client_id:
            try:
                client = Client.objects.get(id=client_id)
            except Client.DoesNotExist:
                logger.warning(f"Client with ID {client_id} not found")
        
        if loan_id:
            try:
                loan = MarginLoan.objects.get(id=loan_id)
            except MarginLoan.DoesNotExist:
                logger.warning(f"Loan with ID {loan_id} not found")

        AuditLog.objects.create(
            event_type=event.get("type"),
            client=client,
            loan=loan,
            details=event,
        )
        logger.info(f"📝 AuditLog saved: {event.get('type')}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to save AuditLog: {e} | event={event}")
        return False

def create_kafka_consumer(topic, group_id):
    """Create and configure Kafka consumer with retry logic"""
    max_retries = 5
    retry_delay = 5  # seconds
    
    for attempt in range(max_retries):
        try:
            consumer = KafkaConsumer(
                topic,
                bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
                auto_offset_reset="earliest",
                enable_auto_commit=True,
                group_id=group_id,
                value_deserializer=safe_deserializer,
                session_timeout_ms=30000,
                heartbeat_interval_ms=3000,
                max_poll_interval_ms=300000,
                # Important: prevent immediate exit on no messages
                consumer_timeout_ms=None  # ← CHANGE THIS: Wait indefinitely for messages
            )
            
            logger.info(f"✅ Successfully connected to Kafka for topic '{topic}'")
            return consumer
            
        except NoBrokersAvailable:
            logger.warning(f"⚠️ No Kafka brokers available (attempt {attempt + 1}/{max_retries})")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                continue
            else:
                logger.error("💥 Failed to connect to Kafka after multiple attempts")
                raise
        except Exception as e:
            logger.error(f"💥 Error creating Kafka consumer: {e}")
            raise

# Handlers
def handle_portfolio_event(event: dict):
    """Process portfolio events"""
    try:
        logger.info(f"📦 Processing portfolio event: {event.get('type')}")
        
        if event.get("type") == "FORCED_SELL":
            logger.warning(f"⚠️ Forced Sell triggered: {event}")
            client_id = event.get("client_id")
            
            # Save audit log
            save_audit_log(event, client_id=client_id)
            
            # TODO: Implement forced sell logic
            logger.info(f"Would execute forced sell for client {client_id}")
            
    except Exception as e:
        logger.error(f"❌ Error in portfolio event handler: {e}", exc_info=True)

def handle_margin_event(event: dict):
    """Process margin events"""
    try:
        logger.info(f"💰 Processing margin event: {event.get('type')}")
        
        if event.get("type") == "MARGIN_REQUEST":
            logger.info(f"💰 Margin Request received: {event}")
            client_id = event.get("client_id")
            loan_id = event.get("loan_id")
            
            # Save audit log
            save_audit_log(event, client_id=client_id, loan_id=loan_id)
            
            # TODO: Business logic for margin approval/rejection
            logger.info(f"Would process margin request for client {client_id}")
            
    except Exception as e:
        logger.error(f"❌ Error in margin event handler: {e}", exc_info=True)

def start_consumer(topic: str, group_id: str, handler_func):
    """Generic Kafka consumer runner with topic verification"""
    consumer = None
    
    try:
        logger.info(f"🚀 Starting {topic} consumer for group {group_id}...")
        
        # Create consumer with retry logic
        consumer = create_kafka_consumer(topic, group_id)
        
        # Verify topic exists and has partitions
        try:
            cluster_metadata = consumer.list_topics()
            if topic not in cluster_metadata.topics:
                logger.warning(f"⚠️ Topic '{topic}' does not exist. Creating by sending test message...")
                
                # Send test message to auto-create topic
                producer = KafkaProducer(bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS)
                producer.send(topic, value=json.dumps({"type": "TEST_CREATION"}).encode('utf-8'))
                producer.flush()
                producer.close()
                
                # Wait a bit for topic creation
                time.sleep(2)
                
                # Refresh metadata
                consumer.list_topics()
        except Exception as e:
            logger.warning(f"⚠️ Could not verify topic '{topic}': {e}")
        
        logger.info(f"📥 Consumer ready. Waiting for messages on topic '{topic}'...")
        
        # Main consumption loop
        while True:
            try:
                # Poll for messages
                raw_messages = consumer.poll(timeout_ms=1000, max_records=10)
                
                if not raw_messages:
                    # No messages, but continue polling
                    continue
                
                # Process messages
                for tp, messages in raw_messages.items():
                    for message in messages:
                        logger.info(f"📩 Received message from {message.topic}[{message.partition}]@offset{message.offset}")
                        
                        event = message.value
                        if not event:
                            continue

                        logger.info(f"🎯 Processing event: {event}")
                        handler_func(event)
                
                # Commit offsets
                consumer.commit_async()
                
            except KeyboardInterrupt:
                logger.info("🛑 Consumer stopped by user")
                break
            except Exception as e:
                logger.error(f"⚠️ Error in consumption loop: {e}", exc_info=True)
                time.sleep(5)
                
    except Exception as e:
        logger.error(f"💥 Fatal error in consumer startup: {e}", exc_info=True)
    finally:
        if consumer:
            consumer.close()

# Dispatcher entrypoint
# core/consumers.py - Fixed version
if __name__ == "__main__":
    import sys

    consumer_type = sys.argv[1] if len(sys.argv) > 1 else "portfolio"

    if consumer_type == "portfolio":
        start_consumer("portfolio-events", "oms-portfolio-group", handle_portfolio_event)
    elif consumer_type == "margin":
        start_consumer("margin-loan-events", "oms-margin-group", handle_margin_event)
    else:
        logger.error("❌ Unknown consumer type. Use: portfolio | margin")
        sys.exit(1)