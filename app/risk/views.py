from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema

from risk.models import ClientRiskProfile
from risk.serializers import ClientRiskProfileSerializer
from risk.services.risk_engine import RiskEngine


class ClientRiskProfileViewSet(viewsets.ModelViewSet):
    """
    Risk profile management API
    """
    queryset = ClientRiskProfile.objects.select_related("client")
    serializer_class = ClientRiskProfileSerializer
    http_method_names = ["get", "post"]  # 🔒 no PUT/PATCH/DELETE

    # --------------------------------
    # RECALCULATE MAX EXPOSURE
    # --------------------------------
    @extend_schema(
        description="Recalculate max exposure (cash × leverage)",
    )
    @action(detail=True, methods=["post"])
    def recalculate(self, request, pk=None):
        risk = self.get_object()
        risk.recalculate()

        # Enforce margin policy after recalculation
        RiskEngine.enforce_margin_policy(risk.client_id)

        return Response(
            {
                "client_id": risk.client_id,
                "max_exposure": str(risk.max_exposure),
                "allow_margin": risk.allow_margin,
            }
        )

    # --------------------------------
    # LIVE UTILIZATION / EDR
    # --------------------------------
    @extend_schema(
        description="Get live margin utilization (EDR%), exposure and status",
    )
    @action(detail=True, methods=["get"])
    def utilization(self, request, pk=None):
        risk = self.get_object()
        client = risk.client

        used = RiskEngine.calculate_current_exposure(client.id)
        loan = RiskEngine.loan_amount(client.id)
        edr = RiskEngine.margin_utilization(client.id)

        return Response(
            {
                "client_id": client.id,
                "client_name": client.name,
                "cash_balance": str(client.cash_balance),
                "used_exposure": str(used),
                "loan_amount": str(loan),              # ✅
                "max_exposure": str(risk.max_exposure),
                "edr_percent": str(edr),
                "edr_status": RiskEngine.utilization_status(client.id),
                "allow_margin": risk.allow_margin,
            }
        )



    # --------------------------------
    # MANUAL MARGIN TOGGLE (ADMIN)
    # --------------------------------
    @extend_schema(
        description="Manually enable/disable margin (Admin override)",
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

        # ✅ Safe boolean parsing
        if isinstance(allow, bool):
            value = allow
        elif isinstance(allow, str):
            value = allow.lower() in ("true", "1", "yes")
        else:
            value = False

        risk.allow_margin = value
        risk.save(update_fields=["allow_margin"])

        return Response(
            {
                "client_id": risk.client_id,
                "allow_margin": risk.allow_margin,
            }
        )
