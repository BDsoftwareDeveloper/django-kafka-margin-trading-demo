# risk/models.py
from decimal import Decimal
from django.db import models


class ClientRiskProfile(models.Model):
    client = models.OneToOneField("core.Client", on_delete=models.CASCADE)
    allow_margin = models.BooleanField(default=True)

    leverage_multiplier = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=Decimal("1.00"),
    )

    max_exposure = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def calculate_max_exposure(self):
        """
        Core risk formula:
        max_exposure = cash_balance × leverage
        """
        cash = self.client.cash_balance or Decimal("0")
        return cash * self.leverage_multiplier

    def recalculate(self, save=True):
        """
        Explicit recalculation entry point
        """
        self.max_exposure = self.calculate_max_exposure()
        if save:
            self.save(update_fields=["max_exposure"])

    def __str__(self):
        return f"RiskProfile(client={self.client_id}, max={self.max_exposure})"
