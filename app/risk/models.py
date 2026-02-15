# risk/models.py
from decimal import Decimal
from django.db import models


class ClientRiskProfile(models.Model):
    client = models.OneToOneField(
        "core.Client",
        on_delete=models.CASCADE,
        related_name="risk_profile",
    )

    allow_margin = models.BooleanField(default=True)

    leverage_multiplier = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=Decimal("1.00"),
    )

    # NEW: maintenance threshold (for MARGIN_CALL logic)
    maintenance_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("75.00"),  # example: 75%
    )

    max_exposure = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    created_at = models.DateTimeField(auto_now_add=True)

    # ------------------------------------------------
    # CORE FORMULA
    # ------------------------------------------------
    def calculate_max_exposure(self):
        """
        max_exposure = (cash + collateral) × leverage
        """

        cash = self.client.cash_balance or Decimal("0.00")
        collateral = self.client.collateral_value or Decimal("0.00")

        base_equity = cash + collateral

        return (base_equity * self.leverage_multiplier).quantize(
            Decimal("0.01")
        )

    def recalculate(self, save=True):
        self.max_exposure = self.calculate_max_exposure()

        if save:
            self.save(update_fields=["max_exposure"])

    def __str__(self):
        return f"RiskProfile(client={self.client_id}, max={self.max_exposure})"
