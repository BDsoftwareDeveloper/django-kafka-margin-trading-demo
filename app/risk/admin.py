# risk/admin.py

from django.contrib import admin
from django.utils.html import format_html

from django.db.models import Count


from risk.models import ClientRiskProfile,ExposureTemplate, TemplateInstrument
from risk.services.risk_engine import RiskEngine



from risk.models import ClientGroup
from core.models import Client


@admin.register(ClientGroup)
class ClientGroupAdmin(admin.ModelAdmin):

    list_display = (
        "name",
        "client_count",
        "template_count",
        "is_active",
        "created_at",
    )

    search_fields = ("name",)
    list_filter = ("is_active",)
    readonly_fields = ("created_at",)

    ordering = ("name",)

    def client_count(self, obj):
        return obj.clients.count()

    def template_count(self, obj):
        return obj.exposure_templates.count()
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




# =====================================================
# INLINE: Template ↔ Instrument Mapping
# =====================================================

class TemplateInstrumentInline(admin.TabularInline):
    model = TemplateInstrument
    extra = 1
    autocomplete_fields = ["instrument"]
    fields = (
        "instrument",
        "priority",
        "effective_from",
        "effective_to",
    )
    ordering = ("priority",)
    

@admin.register(ExposureTemplate)
class ExposureTemplateAdmin(admin.ModelAdmin):

    list_display = (
        "name",
        "instrument_list",
        "instrument_count_display",
        "is_active",
        "created_at",
    )

    search_fields = ("name",)
    list_filter = ("is_active",)

    filter_horizontal = ("instruments",)
    readonly_fields = ("created_at",)

    # Optimize DB query
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.prefetch_related("instruments").annotate(
            _instrument_count=Count("instruments")
        )

    # Show instrument list (limited for readability)
    def instrument_list(self, obj):
        instruments = obj.instruments.all()

        if not instruments:
            return "-"

        symbols = [i.symbol for i in instruments[:8]]

        if obj._instrument_count > 8:
            return format_html(
                "{} <span style='color:gray;'>(+{} more)</span>",
                ", ".join(symbols),
                obj._instrument_count - 8,
            )

        return ", ".join(symbols)

    instrument_list.short_description = "Instruments"

    def instrument_count_display(self, obj):
        return format_html("<strong>{}</strong>", obj._instrument_count)

    instrument_count_display.short_description = "Count"
    instrument_count_display.admin_order_field = "_instrument_count"
    
@admin.register(TemplateInstrument)
class TemplateInstrumentAdmin(admin.ModelAdmin):

    list_display = (
        "template",
        "instrument",
        "priority",
        "effective_from",
        "effective_to",
    )

    list_filter = ("template",)
    search_fields = (
        "template__name",
        "instrument__symbol",
    )

    autocomplete_fields = ["template", "instrument"]

    ordering = ("template", "priority")