from rest_framework import serializers
from .models import Client, Instrument, Portfolio, MarginLoan, AuditLog

class ClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = "__all__"

class InstrumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Instrument
        fields = "__all__"

class PortfolioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Portfolio
        fields = "__all__"

class MarginLoanSerializer(serializers.ModelSerializer):
    class Meta:
        model = MarginLoan
        fields = "__all__"
class AuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditLog
        fields = "__all__"