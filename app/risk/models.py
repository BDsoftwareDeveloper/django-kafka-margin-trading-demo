# risk/models.py
from decimal import Decimal
from django.db import models
from core.models import Client
from core.models import Instrument
from django.utils import timezone


from django.core.exceptions import ValidationError

from django.db.models import Q

class ClientGroup(models.Model):

    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

# class ExposureTemplate(models.Model):

#     name = models.CharField(max_length=100, unique=True)
#     description = models.TextField(blank=True, null=True)

#     instruments = models.ManyToManyField(
#         Instrument,
#         related_name="exposure_templates",
#         blank=True,
#     )

#     max_exposure_percent = models.DecimalField(
#         max_digits=6,
#         decimal_places=2,
#         null=True,
#         blank=True,
#         help_text="Maximum exposure allowed as percentage of net equity",
#     )

#     is_active = models.BooleanField(default=True)
#     is_system = models.BooleanField(default=False)

#     created_at = models.DateTimeField(auto_now_add=True)

#     class Meta:
#         ordering = ["name"]
#         indexes = [
#             models.Index(fields=["is_active"]),
#             models.Index(fields=["is_system"]),
#         ]
#         constraints = [
#             models.CheckConstraint(
#                 check=Q(max_exposure_percent__gte=0) &
#                       Q(max_exposure_percent__lte=100),
#                 name="max_exposure_percent_between_0_100",
#             )
#         ]

#     def save(self, *args, **kwargs):
#         if self.is_system:
#             if ExposureTemplate.objects.exclude(pk=self.pk).filter(is_system=True).exists():
#                 raise ValidationError("Only one system template is allowed.")
#         super().save(*args, **kwargs)

#     def delete(self, *args, **kwargs):
#         if self.is_system:
#             raise ValidationError("System template cannot be deleted.")
#         super().delete(*args, **kwargs)

#     def instrument_count(self):
#         return self.instruments.count()

#     def __str__(self):
#         return self.name





class ExposureTemplate(models.Model):

    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)

    # Instruments in this template
    instruments = models.ManyToManyField(
        Instrument,
        related_name="exposure_templates",
        blank=True,
    )

    # Assign template to client groups
    client_groups = models.ManyToManyField(
        "risk.ClientGroup",
        related_name="exposure_templates",
        blank=True,
    )

    max_exposure_percent = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Maximum exposure allowed as percentage of net equity",
    )

    is_active = models.BooleanField(default=True)
    is_system = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["is_active"]),
            models.Index(fields=["is_system"]),
        ]
        constraints = [
            models.CheckConstraint(
                check=Q(max_exposure_percent__gte=0) &
                      Q(max_exposure_percent__lte=100),
                name="max_exposure_percent_between_0_100",
            )
        ]

    def save(self, *args, **kwargs):
        # Only one system template allowed
        if self.is_system:
            if ExposureTemplate.objects.exclude(pk=self.pk).filter(is_system=True).exists():
                raise ValidationError("Only one system template is allowed.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.is_system:
            raise ValidationError("System template cannot be deleted.")
        super().delete(*args, **kwargs)

    def instrument_count(self):
        return self.instruments.count()

    def group_count(self):
        return self.client_groups.count()

    def __str__(self):
        return self.name

class TemplateInstrument(models.Model):

    template = models.ForeignKey(
        ExposureTemplate,
        on_delete=models.CASCADE
    )

    instrument = models.ForeignKey(
        Instrument,
        on_delete=models.CASCADE
    )

    priority = models.IntegerField(
        default=1,
        help_text="Lower value = higher priority"
    )

    effective_from = models.DateTimeField(null=True, blank=True)
    effective_to = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("template", "instrument")
        ordering = ["priority"]

    def is_active(self):
        now = timezone.now()
        if self.effective_from and now < self.effective_from:
            return False
        if self.effective_to and now > self.effective_to:
            return False
        return True

    def __str__(self):
        return f"{self.template.name} → {self.instrument.symbol}"
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
