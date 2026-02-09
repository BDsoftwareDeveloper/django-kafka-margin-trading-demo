from django.db import models
from django.utils import timezone
from decimal import Decimal



class Instrument(models.Model):
    BOARD_CHOICES = (
        ("A", "A Board"),
        ("B", "B Board"),
        ("Z", "Z Board"),
    )

    symbol = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)
    exchange = models.CharField(max_length=20)

    board = models.CharField(
        max_length=1,
        choices=BOARD_CHOICES,
        default="A",
    )

    is_marginable = models.BooleanField(default=False)
    margin_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.50"),
    )

    def effective_margin_rate(self) -> Decimal:
        """
        Final margin rate after board rules
        """
        if not self.is_marginable:
            return Decimal("0.00")

        if self.board == "Z":
            return Decimal("0.00")  # ❌ Z board margin forbidden

        if self.board == "B":
            return self.margin_rate * Decimal("0.75")  # tighter

        return self.margin_rate  # A board

    def __str__(self):
        return self.symbol



class Client(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)

    cash_balance = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    collateral_value = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


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

    quantity = models.DecimalField(max_digits=20, decimal_places=4)
    avg_price = models.DecimalField(max_digits=20, decimal_places=4)

    class Meta:
        unique_together = ("client", "instrument")

    def market_value(self, market_price: Decimal | None = None) -> Decimal:
        price = market_price or self.avg_price
        return (self.quantity * price).quantize(Decimal("0.01"))

    def margin_value(self, market_price: Decimal | None = None) -> Decimal:
        """
        Margin-eligible value (instrument rules only)
        """
        return (
            self.market_value(market_price)
            * self.instrument.effective_margin_rate()
        ).quantize(Decimal("0.01"))

    def __str__(self):
        return f"{self.client} - {self.instrument}"


class MarginLoan(models.Model):
    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name="margin_loans",
    )

    loan_amount = models.DecimalField(max_digits=20, decimal_places=4)
    interest_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.08"),
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Loan({self.client}, {self.loan_amount})"




class AuditLog(models.Model):
    event_type = models.CharField(max_length=50)

    client = models.ForeignKey(
        Client,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
    )

    loan = models.ForeignKey(
        MarginLoan,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
    )

    details = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @classmethod
    def log_event(cls, event_type, client=None, loan=None, details=None):
        return cls.objects.create(
            event_type=event_type,
            client=client,
            loan=loan,
            details=details or {},
        )

    def __str__(self):
        return f"{self.event_type} @ {self.created_at}"

