from django.db import models
from django.utils import timezone
from decimal import Decimal

class Client(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Instrument(models.Model):
    symbol = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)
    exchange = models.CharField(max_length=20)
    is_marginable = models.BooleanField(default=False)
    margin_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.50)

    def __str__(self):
        return f"{self.symbol} ({'Marginable' if self.is_marginable else 'Non-Marginable'})"


class Portfolio(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    instrument = models.ForeignKey(Instrument, on_delete=models.CASCADE)
    quantity = models.DecimalField(max_digits=20, decimal_places=4)
    avg_price = models.DecimalField(max_digits=20, decimal_places=4)

    class Meta:
        unique_together = ("client", "instrument")

    def current_value(self, market_price: Decimal):
        """Calculate portfolio value for this instrument"""
        return self.quantity * market_price


class MarginLoan(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    loan_amount = models.DecimalField(max_digits=20, decimal_places=4)
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.08)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def is_eligible(self, portfolio_value: Decimal, margin_rate: Decimal):
        """Check if loan is within allowable margin ratio"""
        return self.loan_amount <= portfolio_value * margin_rate


class AuditLog(models.Model):
    event_type = models.CharField(max_length=50)   # ✅ field name
    client = models.ForeignKey(Client, on_delete=models.SET_NULL, null=True, blank=True)
    loan = models.ForeignKey(MarginLoan, on_delete=models.SET_NULL, null=True, blank=True)
    details = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


    @classmethod
    def log_event(cls, event_type, client=None, loan=None, details=None):
        """Helper for logging events"""
        return cls.objects.create(
            event_type=event_type,
            client=client,
            loan=loan,
            details=details or {},
            created_at=timezone.now(),
        )
