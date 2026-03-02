# risk/models.py
from decimal import Decimal
from django.db import models, transaction
from django.core.exceptions import ValidationError
from django.db.models import Q, F, Max
from core.models import Client
from core.models import Instrument
from django.utils import timezone



class ClientGroup(models.Model):

    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class ExposureTemplate(models.Model):

    # ---------------------------------
    # TEMPLATE TYPE
    # ---------------------------------
    TEMPLATE_TYPE_CHOICES = (
        ("MANUAL", "Manual Instruments"),
        ("PE", "PE Based"),
        ("SECTOR", "Sector Based"),
        ("HYBRID", "Sector + PE"),
        ("GLOBAL", "Global Fallback"),
    )

    # Priority tiers (institutional order)
    DEFAULT_PRIORITY_BY_TYPE = {
        "MANUAL": 1,
        "HYBRID": 5,
        "PE": 10,
        "SECTOR": 20,
        "GLOBAL": 999,
    }

    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)

    template_type = models.CharField(
        max_length=20,
        choices=TEMPLATE_TYPE_CHOICES,
        default="PE",
        db_index=True,
    )

    # ---------------------------------
    # Manual Instrument Assignment
    # ---------------------------------
    instruments = models.ManyToManyField(
        "core.Instrument",
        related_name="exposure_templates",
        blank=True,
    )

    # ---------------------------------
    # Dynamic PE Rule
    # ---------------------------------
    min_pe = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )

    max_pe = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )

    # ---------------------------------
    # Sector Rule
    # ---------------------------------
    sector = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        db_index=True,
    )

    # ---------------------------------
    # Group Assignment
    # ---------------------------------
    client_groups = models.ManyToManyField(
        "risk.ClientGroup",
        related_name="exposure_templates",
        blank=True,
    )

    # ---------------------------------
    # Exposure Control
    # ---------------------------------
    max_exposure_percent = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Maximum exposure allowed as percentage of net equity",
    )

    # 🔥 Priority (Backend Controlled)
    priority = models.PositiveIntegerField(
        unique=True,
        db_index=True,
        help_text="Lower number = higher priority",
    )

    is_active = models.BooleanField(default=True)
    is_system = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    # ---------------------------------
    # META
    # ---------------------------------
    class Meta:
        ordering = ["priority", "name"]
        indexes = [
            models.Index(fields=["is_active"]),
            models.Index(fields=["is_system"]),
            models.Index(fields=["template_type"]),
            models.Index(fields=["sector"]),
        ]
        constraints = [
            models.CheckConstraint(
                check=Q(max_exposure_percent__gte=0) &
                      Q(max_exposure_percent__lte=100),
                name="max_exposure_percent_between_0_100",
            ),
            models.CheckConstraint(
                check=Q(min_pe__lte=F("max_pe")) |
                      Q(min_pe__isnull=True) |
                      Q(max_pe__isnull=True),
                name="valid_pe_range",
            ),
        ]

    # ---------------------------------
    # PRIORITY GENERATION
    # ---------------------------------
    def _generate_priority(self):

        base = self.DEFAULT_PRIORITY_BY_TYPE.get(self.template_type, 100)

        # GLOBAL always fixed
        if self.template_type == "GLOBAL":
            return 999

        # MANUAL always highest
        if self.template_type == "MANUAL":
            return 1

        # Find highest priority within this tier block
        max_priority = ExposureTemplate.objects.filter(
            priority__gte=base,
            priority__lt=base + 5
        ).aggregate(Max("priority"))["priority__max"]

        if max_priority:
            return max_priority + 1

        return base

    # ---------------------------------
    # VALIDATION
    # ---------------------------------
    def clean(self):

        # PE validation
        if self.min_pe is not None and self.max_pe is not None:
            if self.min_pe > self.max_pe:
                raise ValidationError("min_pe cannot be greater than max_pe.")

        # Only one system template allowed
        if self.is_system:
            if ExposureTemplate.objects.exclude(pk=self.pk).filter(is_system=True).exists():
                raise ValidationError("Only one system template is allowed.")

        # GLOBAL template must not have rule filters
        if self.template_type == "GLOBAL":
            if (
                self.min_pe is not None
                or self.max_pe is not None
                or self.sector is not None
            ):
                raise ValidationError(
                    "GLOBAL template cannot have PE or sector rules."
                )

    # ---------------------------------
    # SAVE (Auto Priority)
    # ---------------------------------
    @transaction.atomic
    def save(self, *args, **kwargs):

        # Auto assign priority only on create
        if not self.pk:
            self.priority = self._generate_priority()

        super().save(*args, **kwargs)

    # ---------------------------------
    # DELETE PROTECTION
    # ---------------------------------
    def delete(self, *args, **kwargs):
        if self.is_system:
            raise ValidationError("System template cannot be deleted.")
        super().delete(*args, **kwargs)

    # ---------------------------------
    # HELPERS
    # ---------------------------------
    def instrument_count(self):
        return self.instruments.count()

    def group_count(self):
        return self.client_groups.count()

    def __str__(self):
        return f"{self.name} ({self.template_type})"

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
