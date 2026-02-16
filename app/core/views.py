from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema

from decimal import Decimal
from django.db import transaction

from core.models import (
    Client,
    Instrument,
    Portfolio,
    MarginLoan,
    AuditLog,
)

from core.serializers import (
    ClientSerializer,
    InstrumentSerializer,
    PortfolioSerializer,
    MarginLoanSerializer,
    AuditLogSerializer,
)

from core.services.trade_execution import TradeExecutionService
from risk.services.risk_engine import RiskEngine, RiskViolation


# =====================================================
# CLIENT VIEWSET
# =====================================================

@extend_schema(tags=["Clients"])
class ClientViewSet(viewsets.ModelViewSet):
    queryset = Client.objects.all()
    serializer_class = ClientSerializer


# =====================================================
# INSTRUMENT VIEWSET
# =====================================================

@extend_schema(tags=["Instruments"])
class InstrumentViewSet(viewsets.ModelViewSet):
    queryset = Instrument.objects.all()
    serializer_class = InstrumentSerializer


# =====================================================
# PORTFOLIO VIEWSET (Trade Execution Entry Point)
# =====================================================

@extend_schema(tags=["Trading"])
class PortfolioViewSet(viewsets.ModelViewSet):
    queryset = Portfolio.objects.all()
    serializer_class = PortfolioSerializer

    def create(self, request, *args, **kwargs):
        """
        BUY execution endpoint.
        Routes through TradeExecutionService.
        """

        client_id = request.data.get("client")
        instrument_id = request.data.get("instrument")
        quantity = Decimal(request.data.get("quantity"))
        price = Decimal(request.data.get("avg_price"))

        instrument = Instrument.objects.get(id=instrument_id)

        try:
            RiskEngine.check_pre_trade(
                client_id=client_id,
                instrument=instrument,
                side="BUY",
                quantity=quantity,
                price=price,
                is_margin=True,
            )

            TradeExecutionService.execute_trade(
                client_id=client_id,
                instrument=instrument,
                side="BUY",
                quantity=quantity,
                price=price,
            )

            return Response({"status": "trade executed"})

        except RiskViolation as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

    # --------------------------------------------
    # Loan Eligibility
    # --------------------------------------------

    @action(detail=False, methods=["post"], url_path="loan-eligibility")
    def loan_eligibility(self, request):

        client_id = request.data.get("client_id")
        if not client_id:
            return Response({"error": "client_id required"}, status=400)

        portfolios = (
            Portfolio.objects
            .filter(client_id=client_id)
            .select_related("instrument")
        )

        total_eligible = Decimal("0.00")
        details = []

        for p in portfolios:
            if p.instrument.is_marginable:

                eligible = (
                    p.quantity *
                    p.avg_price *
                    p.instrument.initial_margin_rate
                ).quantize(Decimal("0.01"))

                total_eligible += eligible

                details.append({
                    "instrument": p.instrument.symbol,
                    "eligible": str(eligible),
                })

        return Response({
            "client_id": client_id,
            "eligible_amount": str(total_eligible),
            "details": details,
        })

    # --------------------------------------------
    # Force Liquidation
    # --------------------------------------------

    @action(detail=False, methods=["post"], url_path="force-sell")
    def force_sell(self, request):

        client_id = request.data.get("client_id")
        if not client_id:
            return Response({"error": "client_id required"}, status=400)

        try:
            RiskEngine.auto_liquidate(client_id)

            return Response({
                "client_id": client_id,
                "status": "liquidation executed"
            })

        except Exception as e:
            return Response(
                {"error": str(e)},
                status=400
            )


# =====================================================
# MARGIN LOAN VIEWSET (READ ONLY)
# =====================================================

@extend_schema(tags=["Margin Loans"])
class MarginLoanViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Margin loans are managed automatically by trade engine.
    No manual creation allowed.
    """

    queryset = MarginLoan.objects.all()
    serializer_class = MarginLoanSerializer


# =====================================================
# AUDIT LOG VIEWSET
# =====================================================

@extend_schema(tags=["Audit Logs"])
class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AuditLog.objects.all()
    serializer_class = AuditLogSerializer
