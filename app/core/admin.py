from django.contrib import admin
from decimal import Decimal

from .models import Client, Instrument, MarginLoan, Portfolio, AuditLog
from risk.services.risk_engine import RiskEngine


# -----------------------------
# CLIENT ADMIN (OPS VIEW)
# -----------------------------
@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "email",
        "cash_balance",
        "risk_max_exposure",
        "risk_used_exposure",
        "risk_utilization_pct",
        "created_at",
    ]

    list_editable = ["cash_balance"]
    search_fields = ["name", "email"]
    ordering = ["-created_at"]

    readonly_fields = [
        "risk_max_exposure",
        "risk_used_exposure",
        "risk_utilization_pct",
    ]

    def risk_max_exposure(self, obj):
        return getattr(obj.clientriskprofile, "max_exposure", Decimal("0.00"))
    risk_max_exposure.short_description = "Max Exposure"

    def risk_used_exposure(self, obj):
        return RiskEngine.calculate_current_exposure(obj.id)
    risk_used_exposure.short_description = "Used Exposure"

    def risk_utilization_pct(self, obj):
        return f"{RiskEngine.margin_utilization(obj.id)} %"
    risk_utilization_pct.short_description = "Utilization"


# -----------------------------
# INSTRUMENT ADMIN
# -----------------------------
@admin.register(Instrument)
class InstrumentAdmin(admin.ModelAdmin):
    list_display = [
        "symbol",
        "name",
        "exchange",
        "board",
        "is_marginable",
        "margin_rate",
    ]

    list_filter = [
        "exchange",
        "board",
        "is_marginable",
    ]

    search_fields = ["symbol", "name"]


# -----------------------------
# MARGIN LOAN ADMIN
# -----------------------------
@admin.register(MarginLoan)
class MarginLoanAdmin(admin.ModelAdmin):
    list_display = [
        "client",
        "loan_amount",
        "interest_rate",
        "created_at",
    ]

    list_filter = ["created_at"]
    search_fields = ["client__name"]


# -----------------------------
# PORTFOLIO ADMIN
# -----------------------------
@admin.register(Portfolio)
class PortfolioAdmin(admin.ModelAdmin):
    list_display = [
        "client",
        "instrument",
        "quantity",
        "avg_price",
        "position_value",
        "margin_exposure",
    ]

    list_filter = ["instrument__exchange", "instrument__board"]
    search_fields = ["client__name", "instrument__symbol"]

    readonly_fields = ["position_value", "margin_exposure"]

    def position_value(self, obj):
        return obj.quantity * obj.avg_price
    position_value.short_description = "Position Value"

    def margin_exposure(self, obj):
        rate = obj.instrument.effective_margin_rate()
        return obj.quantity * obj.avg_price * rate
    margin_exposure.short_description = "Margin Exposure"


# -----------------------------
# AUDIT LOG ADMIN (READ ONLY)
# -----------------------------
@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = [
        "event_type",
        "client",
        "created_at",
    ]

    list_filter = ["event_type", "created_at"]
    readonly_fields = ["created_at"]
