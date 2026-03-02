# risk/admin.py

from django.contrib import admin
from django.utils.html import format_html

from django.db.models import Count


from risk.models import ClientRiskProfile,ExposureTemplate, TemplateInstrument
from risk.services.risk_engine import RiskEngine



from risk.models import ClientGroup
from core.models import Client, Instrument


from django.db.models import Prefetch


class ClientInline(admin.TabularInline):
    model = Client
    fields = (
        "client_code",
        "name",
        "category",
        "cash_balance",
        "is_active",
    )
    readonly_fields = (
        "client_code",
        "name",
        "category",
        "cash_balance",
        "is_active",
    )
    extra = 0
    show_change_link = True
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

    inlines = [ClientInline]   # 👈 ADD THIS

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
        "template_type_display",
        "priority",
        "rule_summary",
        "instrument_list",
        "instrument_count_display",
        "is_active",
        "created_at",
    )

    search_fields = ("name",)
    list_filter = ("is_active", "template_type")
    filter_horizontal = ("instruments",)

    readonly_fields = ("created_at", "priority")

    ordering = ("priority", "name")

    # --------------------------------------------------
    # Query Optimization
    # --------------------------------------------------
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.prefetch_related("instruments")

    # --------------------------------------------------
    # Template Type Display
    # --------------------------------------------------
    def template_type_display(self, obj):
        return obj.get_template_type_display()

    template_type_display.short_description = "Type"
    template_type_display.admin_order_field = "template_type"

    # --------------------------------------------------
    # Rule Summary (NEW - Enterprise Clarity)
    # --------------------------------------------------
    def rule_summary(self, obj):

        if obj.template_type == "MANUAL":
            return "Manual instrument mapping"

        if obj.template_type == "GLOBAL":
            return "All active instruments"

        parts = []

        if obj.sector:
            parts.append(f"Sector: {obj.sector}")

        if obj.min_pe is not None or obj.max_pe is not None:
            parts.append(f"PE: {obj.min_pe or '-'} → {obj.max_pe or '-'}")

        return " | ".join(parts) if parts else "-"

    rule_summary.short_description = "Rule"

    # --------------------------------------------------
    # Central Instrument Resolver
    # --------------------------------------------------
    def _resolve_instruments(self, obj):

        # Manual
        if obj.template_type == "MANUAL":
            return obj.instruments.all()

        qs = Instrument.objects.filter(is_active=True)

        # GLOBAL
        if obj.template_type == "GLOBAL":
            return qs

        # SECTOR / HYBRID
        if obj.template_type in ["SECTOR", "HYBRID"] and obj.sector:
            qs = qs.filter(sector=obj.sector)

        # PE / HYBRID
        if obj.template_type in ["PE", "HYBRID"]:
            if obj.min_pe is not None:
                qs = qs.filter(pe_ratio__gte=obj.min_pe)
            if obj.max_pe is not None:
                qs = qs.filter(pe_ratio__lte=obj.max_pe)

        return qs

    # --------------------------------------------------
    # Show Instrument List (Optimized)
    # --------------------------------------------------
    def instrument_list(self, obj):

        instruments = self._resolve_instruments(obj)

        symbols = list(
            instruments.values_list("symbol", flat=True)[:9]
        )

        count = len(symbols)

        if count == 0:
            return "-"

        # Check if more exist
        more_exists = instruments.count() > 8

        if more_exists:
            return format_html(
                "{} <span style='color:gray;'>(+ more)</span>",
                ", ".join(symbols[:8]),
            )

        return ", ".join(symbols)

    instrument_list.short_description = "Instruments"

    # --------------------------------------------------
    # Instrument Count (Single Query)
    # --------------------------------------------------
    def instrument_count_display(self, obj):
        count = self._resolve_instruments(obj).count()
        return format_html("<strong>{}</strong>", count)

    instrument_count_display.short_description = "Count"
    
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