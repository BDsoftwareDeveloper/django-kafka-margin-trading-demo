# risk/admin.py

from django.contrib import admin
from django.utils.html import format_html

from risk.models import ClientRiskProfile
from risk.services.risk_engine import RiskEngine


@admin.register(ClientRiskProfile)
class ClientRiskProfileAdmin(admin.ModelAdmin):

    list_display = [
        "client",
        "colored_status",
        "colored_margin_level",
        "net_equity",
        "colored_loan",
        "allow_margin",
        "updated_at",
    ]

    readonly_fields = [
        "colored_status",
        "colored_margin_level",
        "net_equity",
        "colored_loan",
        "updated_at",
    ]

    # ---------------------------------------------------
    # Snapshot Helper
    # ---------------------------------------------------
    def _snapshot(self, obj):
        return RiskEngine.equity_snapshot(obj.client_id)

    # ---------------------------------------------------
    # STATUS (Color-coded)
    # ---------------------------------------------------
    def colored_status(self, obj):
        status = obj.current_status

        color_map = {
            "SAFE": "green",
            "WARNING": "orange",
            "MARGIN_CALL": "#ff8c00",
            "FORCE_SELL": "red",
        }

        return format_html(
            '<strong style="color:{};">{}</strong>',
            color_map.get(status, "black"),
            status,
        )

    colored_status.short_description = "Risk Status"

    # ---------------------------------------------------
    # Margin Level %
    # ---------------------------------------------------
    def colored_margin_level(self, obj):
        snapshot = self._snapshot(obj)
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
            '<strong style="color:{};">{}%</strong>',
            color,
            level,
        )

    colored_margin_level.short_description = "Margin Level %"

    # ---------------------------------------------------
    # Net Equity
    # ---------------------------------------------------
    def net_equity(self, obj):
        snapshot = self._snapshot(obj)
        return snapshot["net_equity"]

    # ---------------------------------------------------
    # Loan Amount
    # ---------------------------------------------------
    def colored_loan(self, obj):
        loan = RiskEngine.loan_amount(obj.client_id)

        if loan == 0:
            return format_html('<span style="color:green;">0.00</span>')

        return format_html(
            '<strong style="color:red;">{}</strong>',
            loan,
        )

    colored_loan.short_description = "Loan Amount"
