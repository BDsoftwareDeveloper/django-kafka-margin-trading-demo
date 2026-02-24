
from core.pagination import StandardResultsSetPagination
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema


from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from decimal import Decimal
from django.db import transaction

from core.models import Portfolio, Instrument, MarginLoan, AuditLog
from core.serializers import PortfolioSerializer
from core.filters import PortfolioFilter
from core.permissions import PortfolioPermission
from core.services.trade_execution import TradeExecutionService
from risk.services.risk_engine import RiskEngine, RiskViolation



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
from core.permissions import( AuditPermission, ClientPermission, InstrumentPermission,
                             MarginLoanPermission, PortfolioPermission)

from core.services.trade_execution import TradeExecutionService
from risk.services.risk_engine import RiskEngine, RiskViolation


# =====================================================
# CLIENT VIEWSET
# =====================================================

# @extend_schema(tags=["Clients"])
# class ClientViewSet(viewsets.ModelViewSet):
#     permission_classes = [AllowAny]
#     queryset = Client.objects.all()
#     serializer_class = ClientSerializer
@extend_schema(tags=["Clients"])
class ClientViewSet(viewsets.ModelViewSet):

    serializer_class = ClientSerializer
    permission_classes = [IsAuthenticated, ClientPermission]

    queryset = Client.objects.all()

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]

    filterset_fields = ["client_code"]
    search_fields = ["client_code", "name", "email"]
    ordering_fields = ["created_at", "client_code"]
    ordering = ["-created_at"]



# =====================================================
# INSTRUMENT VIEWSET
# =====================================================

# @extend_schema(tags=["Instruments"])
# class InstrumentViewSet(viewsets.ModelViewSet):
#     permission_classes = [AllowAny]
#     queryset = Instrument.objects.all()
#     serializer_class = InstrumentSerializer

@extend_schema(tags=["Instruments"])
class InstrumentViewSet(viewsets.ModelViewSet):

    serializer_class = InstrumentSerializer
    permission_classes = [IsAuthenticated, InstrumentPermission]

    queryset = Instrument.objects.all()

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]

    filterset_fields = ["is_marginable"]
    search_fields = ["symbol", "name"]
    ordering_fields = ["symbol", "initial_margin_rate"]
    ordering = ["symbol"]



# =====================================================
# PORTFOLIO VIEWSET (Trade Execution Entry Point)
# =====================================================

# @extend_schema(tags=["Trading"])
# class PortfolioViewSet(viewsets.ModelViewSet):
#     permission_classes = [AllowAny]
#     queryset = Portfolio.objects.all()
#     serializer_class = PortfolioSerializer

#     def create(self, request, *args, **kwargs):
#         """
#         BUY execution endpoint.
#         Routes through TradeExecutionService.
#         """

#         client_id = request.data.get("client")
#         instrument_id = request.data.get("instrument")
#         quantity = Decimal(request.data.get("quantity"))
#         price = Decimal(request.data.get("avg_price"))

#         instrument = Instrument.objects.get(id=instrument_id)

#         try:
#             RiskEngine.check_pre_trade(
#                 client_id=client_id,
#                 instrument=instrument,
#                 side="BUY",
#                 quantity=quantity,
#                 price=price,
#                 is_margin=True,
#             )

#             TradeExecutionService.execute_trade(
#                 client_id=client_id,
#                 instrument=instrument,
#                 side="BUY",
#                 quantity=quantity,
#                 price=price,
#             )

#             return Response({"status": "trade executed"})

#         except RiskViolation as e:
#             return Response(
#                 {"error": str(e)},
#                 status=status.HTTP_400_BAD_REQUEST,
#             )

#     # --------------------------------------------
#     # Loan Eligibility
#     # --------------------------------------------

#     @action(detail=False, methods=["post"], url_path="loan-eligibility")
#     def loan_eligibility(self, request):

#         client_id = request.data.get("client_id")
#         if not client_id:
#             return Response({"error": "client_id required"}, status=400)

#         portfolios = (
#             Portfolio.objects
#             .filter(client_id=client_id)
#             .select_related("instrument")
#         )

#         total_eligible = Decimal("0.00")
#         details = []

#         for p in portfolios:
#             if p.instrument.is_marginable:

#                 eligible = (
#                     p.quantity *
#                     p.avg_price *
#                     p.instrument.initial_margin_rate
#                 ).quantize(Decimal("0.01"))

#                 total_eligible += eligible

#                 details.append({
#                     "instrument": p.instrument.symbol,
#                     "eligible": str(eligible),
#                 })

#         return Response({
#             "client_id": client_id,
#             "eligible_amount": str(total_eligible),
#             "details": details,
#         })

#     # --------------------------------------------
#     # Force Liquidation
#     # --------------------------------------------

#     @action(detail=False, methods=["post"], url_path="force-sell")
#     def force_sell(self, request):

#         client_id = request.data.get("client_id")
#         if not client_id:
#             return Response({"error": "client_id required"}, status=400)

#         try:
#             RiskEngine.auto_liquidate(client_id)

#             return Response({
#                 "client_id": client_id,
#                 "status": "liquidation executed"
#             })

#         except Exception as e:
#             return Response(
#                 {"error": str(e)},
#                 status=400
#             )

@extend_schema(tags=["Trading"])

class PortfolioViewSet(viewsets.ModelViewSet):

    serializer_class = PortfolioSerializer
    permission_classes = [IsAuthenticated, PortfolioPermission]

    queryset = Portfolio.objects.select_related("client", "instrument")

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = PortfolioFilter

    search_fields = [
        "client__client_code",
        "instrument__symbol",
    ]

    ordering_fields = [
    "quantity",
    "avg_price",
    "updated_at",   # ✅ correct field
    ]

    ordering = ["-updated_at"]


    # ---------------------------------
    # BUY Trade (Atomic)
    # ---------------------------------
    @transaction.atomic
    def create(self, request, *args, **kwargs):

        client_id = request.data.get("client")
        instrument_id = request.data.get("instrument")
        quantity = Decimal(request.data.get("quantity"))
        price = Decimal(request.data.get("avg_price"))

        try:
            instrument = Instrument.objects.get(id=instrument_id)

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

        except Instrument.DoesNotExist:
            return Response(
                {"error": "Invalid instrument"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        except RiskViolation as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

    # ---------------------------------
    # Loan Eligibility
    # ---------------------------------
    @action(detail=False, methods=["post"])
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

    # ---------------------------------
    # Force Liquidation
    # ---------------------------------
    @action(detail=False, methods=["post"], url_path="force-sell")
    @transaction.atomic
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
            return Response({"error": str(e)}, status=400)



# =====================================================
# MARGIN LOAN VIEWSET (READ ONLY)
# =====================================================

# @extend_schema(tags=["Margin Loans"])
# class MarginLoanViewSet(viewsets.ReadOnlyModelViewSet):
#     """
#     Margin loans are managed automatically by trade engine.
#     No manual creation allowed.
#     """
#     permission_classes = [AllowAny]

#     queryset = MarginLoan.objects.all()
#     serializer_class = MarginLoanSerializer

@extend_schema(tags=["Margin Loans"])
class MarginLoanViewSet(viewsets.ReadOnlyModelViewSet):

    serializer_class = MarginLoanSerializer
    permission_classes = [IsAuthenticated, MarginLoanPermission]
    pagination_class = StandardResultsSetPagination

    queryset = MarginLoan.objects.select_related("client")

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]

    filterset_fields = ["client"]
    search_fields = ["client__client_code"]

    ordering_fields = ["principal_amount", "opened_at", "status"]
    ordering = ["-opened_at"]




# =====================================================
# AUDIT LOG VIEWSET
# =====================================================

# @extend_schema(tags=["Audit Logs"])
# class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
#     permission_classes = [AllowAny]
#     queryset = AuditLog.objects.all()
#     serializer_class = AuditLogSerializer
@extend_schema(tags=["Audit Logs"])
class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):

    serializer_class = AuditLogSerializer
    permission_classes = [IsAuthenticated, AuditPermission]

    queryset = AuditLog.objects.select_related("client")

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]

    filterset_fields = ["action", "client"]
    search_fields = ["description"]
    ordering_fields = ["timestamp"]
    ordering = ["-timestamp"]
