from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import Client, Instrument, MarginLoan, Portfolio, AuditLog

@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'created_at']
    search_fields = ['name', 'email']

@admin.register(Instrument)
class InstrumentAdmin(admin.ModelAdmin):
    list_display = ['symbol', 'name', 'exchange', 'is_marginable', 'margin_rate']
    list_filter = ['exchange', 'is_marginable']
    search_fields = ['symbol', 'name']

@admin.register(MarginLoan)
class MarginLoanAdmin(admin.ModelAdmin):
    list_display = ['client', 'loan_amount', 'interest_rate', 'created_at']
    list_filter = ['created_at']
    search_fields = ['client__name']

@admin.register(Portfolio)
class PortfolioAdmin(admin.ModelAdmin):
    list_display = ['client', 'instrument', 'quantity', 'avg_price']
    list_filter = ['instrument__exchange']

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['event_type', 'client', 'created_at']
    list_filter = ['event_type', 'created_at']
    readonly_fields = ['created_at']