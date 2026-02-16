from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema

from risk.models import ClientRiskProfile
from risk.serializers import ClientRiskProfileSerializer
from risk.services.risk_engine import RiskEngine



from rest_framework.views import APIView
from risk.serializers import HouseRiskSerializer


from risk.services.house_risk_service import HouseRiskService

class ClientRiskProfileViewSet(viewsets.ModelViewSet):
    """
    Institutional Risk Profile API (Equity-Based)
    """

    queryset = ClientRiskProfile.objects.select_related("client")
    serializer_class = ClientRiskProfileSerializer
    http_method_names = ["get"]  # 🔒 read-only (institutional)

    # ---------------------------------------------------
    # LIVE EQUITY SNAPSHOT
    # ---------------------------------------------------
    @extend_schema(
        description="Get real-time institutional equity-based margin snapshot",
    )
    @action(detail=True, methods=["get"])
    def snapshot(self, request, pk=None):

        risk = self.get_object()
        client = risk.client

        snapshot = RiskEngine.equity_snapshot(client.id)

        return Response({
            "client_id": client.id,
            "client_name": client.name,
            "cash_balance": str(client.cash_balance),

            "market_value": str(snapshot["market_value"]),
            "loan": str(snapshot["loan"]),
            "net_equity": str(snapshot["net_equity"]),
            "maintenance_requirement": str(snapshot["maintenance_requirement"]),
            "margin_level_percent": str(snapshot["margin_level_percent"]),

            "margin_status": risk.current_status,
            "allow_margin": risk.allow_margin,

            "thresholds": {
                "warning_level": str(risk.warning_level),
                "margin_call_level": str(risk.margin_call_level),
                "force_sell_level": str(risk.force_sell_level),
            }
        })

    # ---------------------------------------------------
    # FORCE RE-EVALUATE STATUS
    # ---------------------------------------------------
    @extend_schema(
        description="Re-evaluate client margin status (equity-based engine)",
    )
    @action(detail=True, methods=["post"])
    def recheck(self, request, pk=None):

        risk = self.get_object()

        # Run institutional margin engine
        RiskEngine.enforce_margin_policy(risk.client_id)

        snapshot = RiskEngine.equity_snapshot(risk.client_id)

        return Response({
            "client_id": risk.client_id,
            "margin_level_percent": str(snapshot["margin_level_percent"]),
            "new_status": risk.current_status,
            "allow_margin": risk.allow_margin,
        })

    # ---------------------------------------------------
    # ADMIN OVERRIDE
    # ---------------------------------------------------
    @extend_schema(
        description="Manual margin override (Admin only)",
    )
    @action(detail=True, methods=["post"])
    def toggle_margin(self, request, pk=None):

        risk = self.get_object()

        allow = request.data.get("allow_margin")

        if allow is None:
            return Response(
                {"error": "allow_margin is required (true/false)"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if isinstance(allow, bool):
            value = allow
        elif isinstance(allow, str):
            value = allow.lower() in ("true", "1", "yes")
        else:
            value = False

        risk.allow_margin = value
        risk.save(update_fields=["allow_margin"])

        return Response({
            "client_id": risk.client_id,
            "allow_margin": risk.allow_margin,
        })



class HouseRiskDashboardAPIView(APIView):

    @extend_schema(
        tags=["House Risk"],
        responses=HouseRiskSerializer,
        description="Institutional house-level margin monitoring snapshot",
    )
    def get(self, request):

        data = HouseRiskService.snapshot()

        serializer = HouseRiskSerializer(data)
        return Response(serializer.data)
