from rest_framework import serializers
from risk.models import ClientRiskProfile
from risk.services.risk_engine import RiskEngine


class ClientRiskProfileSerializer(serializers.ModelSerializer):

    # ------------------------------
    # Client Info
    # ------------------------------
    client_name = serializers.CharField(
        source="client.name",
        read_only=True
    )

    cash_balance = serializers.DecimalField(
        source="client.cash_balance",
        max_digits=20,
        decimal_places=2,
        read_only=True,
    )

    # ------------------------------
    # Institutional Risk Metrics
    # ------------------------------
    market_value = serializers.SerializerMethodField()
    loan = serializers.SerializerMethodField()
    net_equity = serializers.SerializerMethodField()
    maintenance_requirement = serializers.SerializerMethodField()
    margin_level_percent = serializers.SerializerMethodField()
    margin_status = serializers.SerializerMethodField()

    class Meta:
        model = ClientRiskProfile
        fields = [
            "id",
            "client",
            "client_name",
            "cash_balance",

            # Margin Controls
            "allow_margin",
            "current_status",
            "warning_level",
            "margin_call_level",
            "force_sell_level",

            # Institutional Metrics
            "market_value",
            "loan",
            "net_equity",
            "maintenance_requirement",
            "margin_level_percent",
            "margin_status",
        ]

        read_only_fields = [
            "market_value",
            "loan",
            "net_equity",
            "maintenance_requirement",
            "margin_level_percent",
            "margin_status",
            "current_status",
        ]

    # --------------------------------------------
    # Snapshot (Single Calculation per Row)
    # --------------------------------------------
    def _snapshot(self, obj):
        return RiskEngine.equity_snapshot(obj.client_id)

    def get_market_value(self, obj):
        return str(self._snapshot(obj)["market_value"])

    def get_loan(self, obj):
        return str(self._snapshot(obj)["loan"])

    def get_net_equity(self, obj):
        return str(self._snapshot(obj)["net_equity"])

    def get_maintenance_requirement(self, obj):
        return str(self._snapshot(obj)["maintenance_requirement"])

    def get_margin_level_percent(self, obj):
        return str(self._snapshot(obj)["margin_level_percent"])

    def get_margin_status(self, obj):
        return RiskEngine.evaluate_margin_status(obj.client_id)




class HouseRiskSerializer(serializers.Serializer):

    total_principal = serializers.DecimalField(
        max_digits=20,
        decimal_places=2
    )

    total_interest = serializers.DecimalField(
        max_digits=20,
        decimal_places=2
    )

    total_market_value = serializers.DecimalField(
        max_digits=20,
        decimal_places=2
    )

    total_cash = serializers.DecimalField(
        max_digits=20,
        decimal_places=2
    )

    maintenance_requirement = serializers.DecimalField(
        max_digits=20,
        decimal_places=2
    )

    house_margin_level = serializers.DecimalField(
        max_digits=10,
        decimal_places=2
    )
