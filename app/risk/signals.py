from decimal import Decimal
from django.db.models.signals import post_save
from django.dispatch import receiver

from core.models import Client
from risk.models import ClientRiskProfile
from risk.services.risk_engine import RiskEngine


@receiver(post_save, sender=Client)
def sync_client_risk_profile(sender, instance, created, **kwargs):
    """
    1. Ensure risk profile exists
    2. Recalculate max exposure on cash change
    3. Enforce margin policy (EDR / FORCE_SELL)
    """

    # --- Create risk profile on first client creation ---
    if created:
        ClientRiskProfile.objects.create(
            client=instance,
            allow_margin=True,
            leverage_multiplier=Decimal("1.50"),
        )
        return

    # --- Existing client ---
    try:
        risk = instance.clientriskprofile
    except ClientRiskProfile.DoesNotExist:
        risk = ClientRiskProfile.objects.create(
            client=instance,
            allow_margin=True,
            leverage_multiplier=Decimal("1.50"),
        )

    # --- Recalculate exposure ---
    risk.recalculate()

    # --- Enforce margin policy (SAFE → WARNING → FORCE_SELL) ---
    RiskEngine.enforce_margin_policy(instance.id)
