from django.db import models
from decimal import Decimal

from django.db.models import Q

# ======================================================
# INSTRUMENT
# ======================================================

class Instrument(models.Model):

    BOARD_CHOICES = (
        ("A", "A Board"),
        ("B", "B Board"),
        ("Z", "Z Board"),
    )

    symbol = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)
    exchange = models.CharField(max_length=20)

    board = models.CharField(max_length=1, choices=BOARD_CHOICES)

    is_marginable = models.BooleanField(default=False)

    # Initial Margin (IMR)
    initial_margin_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.50"),
    )

    # Maintenance Margin (MMR)
    maintenance_margin_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.30"),
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.symbol


# ======================================================
# MARKET PRICE (MTM SOURCE)
# ======================================================

class MarketPrice(models.Model):

    instrument = models.OneToOneField(
        Instrument,
        on_delete=models.CASCADE,
        related_name="market_price",
    )

    last_price = models.DecimalField(
        max_digits=20,
        decimal_places=4,
    )

    mark_price = models.DecimalField(
        max_digits=20,
        decimal_places=4,
        null=True,
        blank=True,
    )

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.instrument.symbol} - {self.last_price}"


# ======================================================
# CLIENT
# ======================================================

class Client(models.Model):

    CATEGORY_CHOICES = (
        ("A", "A Type"),
        ("B", "B Type"),
        ("G", "G Type"),
        ("N", "N Type"),
    )

    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)

    category = models.CharField(
        max_length=1,
        choices=CATEGORY_CHOICES,
        default="A",   # Safe default for migration
    )

    # Liquid available cash
    cash_balance = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    # Cash reserved by open BUY orders
    blocked_cash = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    # Collateral pledged manually (optional but recommended)
    collateral_value = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


# ======================================================
# PORTFOLIO (POSITIONS)
# ======================================================

class Portfolio(models.Model):

    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name="portfolios",
    )

    instrument = models.ForeignKey(
        Instrument,
        on_delete=models.CASCADE,
        related_name="portfolios",
    )

    quantity = models.DecimalField(
        max_digits=20,
        decimal_places=4,
        default=Decimal("0.0000"),
    )

    avg_price = models.DecimalField(
        max_digits=20,
        decimal_places=4,
        default=Decimal("0.0000"),
    )

    # Reserved for pending SELL
    blocked_quantity = models.DecimalField(
        max_digits=20,
        decimal_places=4,
        default=Decimal("0.0000"),
    )

    # Shares pledged for collateral margin
    pledged_quantity = models.DecimalField(
        max_digits=20,
        decimal_places=4,
        default=Decimal("0.0000"),
    )

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("client", "instrument")

    def __str__(self):
        return f"{self.client} - {self.instrument}"


# ======================================================
# MARGIN LOAN (LEDGER-BASED)
# ======================================================


class MarginLoan(models.Model):

    STATUS_CHOICES = (
        ("ACTIVE", "Active"),
        ("CLOSED", "Closed"),
        ("LIQUIDATED", "Liquidated"),
    )

    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name="margin_loans",
    )

    principal_amount = models.DecimalField(
        max_digits=20,
        decimal_places=2,
    )

    accrued_interest = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    interest_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.08"),
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="ACTIVE",
    )

    opened_at = models.DateTimeField(auto_now_add=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["client"],
                condition=Q(status="ACTIVE"),
                name="unique_active_margin_loan_per_client",
            )
        ]

    def __str__(self):
        return f"Loan({self.client}, {self.principal_amount}, {self.status})"



# ======================================================
# AUDIT LOG
# ======================================================

class AuditLog(models.Model):

    event_type = models.CharField(max_length=50)

    client = models.ForeignKey(
        Client,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    details = models.JSONField(default=dict)

    created_at = models.DateTimeField(auto_now_add=True)

    @classmethod
    def log_event(cls, event_type, client=None, details=None):
        return cls.objects.create(
            event_type=event_type,
            client=client,
            details=details or {},
        )

    def __str__(self):
        return f"{self.event_type} @ {self.created_at}"

