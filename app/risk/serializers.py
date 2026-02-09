from rest_framework import serializers
from risk.models import ClientRiskProfile
from risk.services.risk_engine import RiskEngine


class ClientRiskProfileSerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source="client.name", read_only=True)
    cash_balance = serializers.DecimalField(
        source="client.cash_balance",
        max_digits=20,
        decimal_places=2,
        read_only=True,
    )

    used_exposure = serializers.SerializerMethodField()
    edr_percent = serializers.SerializerMethodField()
    edr_status = serializers.SerializerMethodField()
    loan_amount = serializers.SerializerMethodField()

    class Meta:
        model = ClientRiskProfile
        fields = [
        "id",
        "client",
        "client_name",
        "cash_balance",
        "allow_margin",
        "leverage_multiplier",
        "max_exposure",
        "used_exposure",
        "loan_amount",        # ✅ NEW
        "edr_percent",
        "edr_status",
        "created_at",
    ]


    def get_loan_amount(self, obj):
        return str(
            RiskEngine.loan_amount(obj.client_id)
        )
        
    def get_used_exposure(self, obj):
        return str(
            RiskEngine.calculate_current_exposure(obj.client_id)
        )

    def get_edr_percent(self, obj):
        return str(
            RiskEngine.margin_utilization(obj.client_id)
        )

    def get_edr_status(self, obj):
        return RiskEngine.utilization_status(obj.client_id)
