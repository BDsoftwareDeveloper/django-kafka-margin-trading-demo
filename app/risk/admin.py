from django.contrib import admin
from .models import ClientRiskProfile


@admin.register(ClientRiskProfile)
class ClientRiskProfileAdmin(admin.ModelAdmin):
    list_display = (
        "client",
        "leverage_multiplier",
        "max_exposure",
        "allow_margin",
    )
    list_editable = ("leverage_multiplier", "allow_margin")
    readonly_fields = ("max_exposure",)

    def has_add_permission(self, request):
        # ❌ prevent manual add (fixes cursor error)
        return False
