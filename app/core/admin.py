from django.contrib import admin
from decimal import Decimal
from django.utils.html import format_html
from .models import Client, Instrument, MarginLoan, Portfolio, AuditLog
from risk.services.risk_engine import RiskEngine


# =============================
# CLIENT ADMIN
# =============================
@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):

    list_display = [
        "name",
        "email",
        "cash_balance",
        "blocked_cash",
        "loan_outstanding",
        "margin_level_display",
        "created_at",
    ]

    list_editable = ["cash_balance"]
    search_fields = ["name", "email"]
    ordering = ["-created_at"]

    def loan_outstanding(self, obj):
        from core.models import MarginLoan

        loan = (
            MarginLoan.objects
            .filter(client=obj, status="ACTIVE")
            .first()
        )

        if not loan:
            return "0.00"

        return f"{(loan.principal_amount + loan.accrued_interest):.2f}"

    loan_outstanding.short_description = "Loan"

    def margin_level_display(self, obj):
        try:
            snapshot = RiskEngine.equity_snapshot(obj.id)
            level = snapshot["margin_level_percent"]

            if level >= 150:
                color = "green"
            elif level >= 120:
                color = "orange"
            elif level >= 100:
                color = "#ff8c00"
            else:
                color = "red"

            return format_html(
                '<strong style="color:{};">{} %</strong>',
                color,
                level,
            )

        except Exception:
            return "—"


    margin_level_display.short_description = "Margin Level %"


# =============================
# INSTRUMENT ADMIN
# =============================
@admin.register(Instrument)
class InstrumentAdmin(admin.ModelAdmin):

    list_display = [
        "symbol",
        "name",
        "exchange",
        "board",
        "is_marginable",
        "initial_margin_rate",
        "maintenance_margin_rate",
        "is_active",
    ]

    list_filter = [
        "exchange",
        "board",
        "is_marginable",
        "is_active",
    ]

    search_fields = ["symbol", "name"]


# =============================
# MARGIN LOAN ADMIN
# =============================
@admin.register(MarginLoan)
class MarginLoanAdmin(admin.ModelAdmin):

    list_display = [
        "client",
        "principal_amount",
        "accrued_interest",
        "interest_rate",
        "status",
        "opened_at",
        "closed_at",
    ]

    list_filter = [
        "status",
        "opened_at",
    ]

    search_fields = ["client__name"]


# =============================
# PORTFOLIO ADMIN
# =============================
@admin.register(Portfolio)
class PortfolioAdmin(admin.ModelAdmin):

    list_display = [
        "client",
        "instrument",
        "quantity",
        "avg_price",
        "position_value",
    ]

    list_filter = [
        "instrument__exchange",
        "instrument__board",
    ]

    search_fields = [
        "client__name",
        "instrument__symbol",
    ]

    readonly_fields = ["position_value"]

    def position_value(self, obj):
        return (obj.quantity * obj.avg_price).quantize(
            Decimal("0.01")
        )

    position_value.short_description = "Position Value"


# =============================
# AUDIT LOG ADMIN
# =============================
@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):

    list_display = [
        "event_type",
        "client",
        "created_at",
    ]

    list_filter = [
        "event_type",
        "created_at",
    ]

    readonly_fields = [
        "event_type",
        "client",
        "details",
        "created_at",
    ]
