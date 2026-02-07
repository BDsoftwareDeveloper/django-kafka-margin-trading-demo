# risk/signals.py
from decimal import Decimal
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from core.models import Client
from risk.models import ClientRiskProfile


@receiver(post_save, sender=Client)
def create_client_risk_profile(sender, instance, created, **kwargs):
    """
    Create risk profile once when client is created
    """
    if created:
        ClientRiskProfile.objects.create(
            client=instance,
            allow_margin=True,
            leverage_multiplier=Decimal("1.50"),
            max_exposure=Decimal("0.00"),
        )


@receiver(pre_save, sender=Client)
def update_risk_on_cash_change(sender, instance, **kwargs):
    if not instance.pk:
        return

    try:
        old = Client.objects.get(pk=instance.pk)
    except Client.DoesNotExist:
        return

    if old.cash_balance != instance.cash_balance:
        try:
            risk = instance.clientriskprofile
            risk.recalculate()
        except ClientRiskProfile.DoesNotExist:
            pass

