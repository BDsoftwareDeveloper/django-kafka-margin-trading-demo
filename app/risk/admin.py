
from django.contrib import admin
from django.utils.html import format_html

from risk.models import ClientRiskProfile
from risk.services.risk_engine import RiskEngine


@admin.register(ClientRiskProfile)
class ClientRiskProfileAdmin(admin.ModelAdmin):
    list_display = [
        "client",
        "max_exposure",
        "used_exposure",
        "edr_percent",
        "edr_status",
        "allow_margin",
        "created_at",
    ]

    list_filter = ["allow_margin"]
    search_fields = ["client__name", "client__email"]
    readonly_fields = ["max_exposure"]

    # ---------- COMPUTED COLUMNS ----------

    def used_exposure(self, obj):
        used = RiskEngine.calculate_current_exposure(obj.client_id)
        return f"{used:.2f}"

    used_exposure.short_description = "Used Exposure"

    def edr_percent(self, obj):
        utilization = RiskEngine.margin_utilization(obj.client_id)

        # Color rules
        if utilization < 50:
            color = "green"
        elif utilization < 75:
            color = "orange"
        elif utilization < 90:
            color = "#ff8c00"
        else:
            color = "red"

        return format_html(
            '<strong style="color:{};">{}%</strong>',
            color,
            utilization,
        )

    edr_percent.short_description = "EDR %"

    def edr_status(self, obj):
        status = RiskEngine.utilization_status(obj.client_id)

        color_map = {
            "SAFE": "green",
            "WARNING": "orange",
            "MARGIN_CALL": "#ff8c00",
            "FORCE_SELL": "red",
        }

        return format_html(
            '<span style="color:{}; font-weight:bold;">{}</span>',
            color_map.get(status, "black"),
            status,
        )

    edr_status.short_description = "Risk Status"
