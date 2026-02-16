# risk/models.py
from decimal import Decimal
from django.db import models
from core.models import Client


class ClientRiskProfile(models.Model):

    STATUS_CHOICES = (
        ("SAFE", "Safe"),
        ("WARNING", "Warning"),
        ("MARGIN_CALL", "Margin Call"),
        ("FORCE_SELL", "Force Sell"),
    )

    client = models.OneToOneField(
        Client,
        on_delete=models.CASCADE,
        related_name="risk_profile",
    )

    # ===============================
    # Margin Level Thresholds
    # ===============================
    warning_level = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal("150.00"),   # 150%
    )

    margin_call_level = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal("130.00"),   # 130%
    )

    force_sell_level = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal("110.00"),   # 110%
    )

    # ===============================
    # System Controls
    # ===============================
    allow_margin = models.BooleanField(default=True)

    current_status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="SAFE",
    )

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"RiskProfile({self.client.name})"
