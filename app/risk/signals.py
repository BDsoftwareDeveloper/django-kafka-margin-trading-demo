from decimal import Decimal
from django.db.models.signals import post_save
from django.dispatch import receiver

from core.models import Client
from risk.models import ClientRiskProfile


# @receiver(post_save, sender=Client)
# def sync_client_risk_profile(sender, instance, created, **kwargs):
#     """
#     1. Ensure ClientRiskProfile exists
#     2. Always keep max_exposure in sync with cash_balance
#     """

#     # --- Create on first client creation ---
#     if created:
#         risk = ClientRiskProfile.objects.create(
#             client=instance,
#             allow_margin=True,
#             leverage_multiplier=Decimal("1.50"),
#         )
#         # ✅ MUST recalc here
#         risk.recalculate()
#         return

#     # --- Existing client ---
#     try:
#         risk = instance.clientriskprofile
#     except ClientRiskProfile.DoesNotExist:
#         risk = ClientRiskProfile.objects.create(
#             client=instance,
#             allow_margin=True,
#             leverage_multiplier=Decimal("1.50"),
#         )

#     # ✅ Always recalc on update
#     risk.recalculate()
@receiver(post_save, sender=Client)
def sync_client_risk_profile(sender, instance, created, **kwargs):

    if created:
        risk = ClientRiskProfile.objects.create(
            client=instance,
            allow_margin=True,
            leverage_multiplier=Decimal("1.50"),
        )
        risk.recalculate()
        return

    try:
        risk = instance.risk_profile
    except ClientRiskProfile.DoesNotExist:
        risk = ClientRiskProfile.objects.create(
            client=instance,
            allow_margin=True,
            leverage_multiplier=Decimal("1.50"),
        )

    risk.recalculate()
