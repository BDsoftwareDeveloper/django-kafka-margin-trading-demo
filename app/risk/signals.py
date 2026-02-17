from django.db.models.signals import post_save
from django.dispatch import receiver

from core.models import Client
from risk.models import ClientRiskProfile


@receiver(post_save, sender=Client)
def sync_client_risk_profile(sender, instance, created, **kwargs):
    """
    Automatically create RiskProfile when Client is created.
    No recalculation here — RiskEngine handles runtime calculations.
    """

    if created:
        ClientRiskProfile.objects.create(
            client=instance,
            allow_margin=True,
        )
