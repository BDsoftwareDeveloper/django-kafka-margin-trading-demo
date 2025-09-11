# core/signals.py
import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from core.models import MarginLoan, Portfolio
from core.producers import publish_margin_request, publish_forced_sell

logger = logging.getLogger(__name__)


@receiver(post_save, sender=MarginLoan)
def marginloan_created(sender, instance, created, **kwargs):
    """Send Kafka event when a MarginLoan is created"""
    if created:
        logger.info(f"📢 MarginLoan created for client={instance.client.id} amount={instance.loan_amount}")
        publish_margin_request(client_id=instance.client.id, amount=float(instance.loan_amount))


@receiver(post_save, sender=Portfolio)
def portfolio_updated(sender, instance, created, **kwargs):
    """Example: If portfolio quantity < 0, force sell event"""
    if not created and instance.quantity < 0:
        logger.warning(f"⚠️ Forced sell triggered for client={instance.client.id}, portfolio={instance.id}")
        publish_forced_sell(
            client_id=instance.client.id,
            portfolio_id=instance.id,
            reason="Negative quantity"
        )
