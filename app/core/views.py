from rest_framework import viewsets
from drf_spectacular.utils import extend_schema, OpenApiExample
from rest_framework.decorators import action
from rest_framework.response import Response

from django.db import transaction
from decimal import Decimal

from rest_framework import status

from .models import MarginLoan, AuditLog
from .serializers import MarginLoanSerializer, AuditLogSerializer
from .producers import KafkaProducerWrapper

from .models import Portfolio, MarginLoan, AuditLog,Client, Instrument
from risk.services.risk_engine import RiskEngine, RiskViolation


from .serializers import (
    ClientSerializer,
    InstrumentSerializer,
    PortfolioSerializer,
    MarginLoanSerializer,
    AuditLogSerializer,  # 🔹 New
)


@extend_schema(
    tags=["Clients"],
    description="Manage clients in the system",
    examples=[
        OpenApiExample(
            "Create Client Example",
            value={"name": "Alice Smith", "email": "alice@example.com"},
            request_only=True,
        ),
        OpenApiExample(
            "Client Response Example",
            value={"id": 1, "name": "Alice Smith", "email": "alice@example.com", "created_at": "2025-09-07T10:00:00Z"},
            response_only=True,
        ),
    ],
)
class ClientViewSet(viewsets.ModelViewSet):
    queryset = Client.objects.all()
    serializer_class = ClientSerializer


@extend_schema(
    tags=["Instruments"],
    description="List and manage tradable instruments",
    examples=[
        OpenApiExample(
            "Instrument Example",
            value={
                "id": 1,
                "symbol": "AAPL",
                "name": "Apple Inc.",
                "exchange": "NASDAQ",
                "is_marginable": True,
                "margin_rate": "0.50",
            },
            response_only=True,
        ),
    ],
)
class InstrumentViewSet(viewsets.ModelViewSet):
    queryset = Instrument.objects.all()
    serializer_class = InstrumentSerializer


@extend_schema(
    tags=["Portfolio"],
    description="Track client holdings and valuations",
    examples=[
        OpenApiExample(
            "Portfolio Example",
            value={
                "id": 1,
                "client": 1,
                "instrument": 1,
                "quantity": "100.0000",
                "avg_price": "150.2500",
            },
            response_only=True,
        ),
    ],
)
class PortfolioViewSet(viewsets.ModelViewSet):
    queryset = Portfolio.objects.all()
    serializer_class = PortfolioSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        client = serializer.validated_data["client"]
        instrument = serializer.validated_data["instrument"]
        quantity = serializer.validated_data["quantity"]
        price = serializer.validated_data["avg_price"]

        # 🔐 RISK CHECK (PRE-TRADE)
        try:
            RiskEngine.check_pre_trade(
                client_id=client.id,
                instrument=instrument,
                side="BUY",
                quantity=Decimal(quantity),
                price=Decimal(price),
                is_margin=True,  # portfolio implies margin exposure
            )
        except RiskViolation as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return super().create(request, *args, **kwargs)

    @extend_schema(
        tags=["Portfolio"],
        description="Check margin loan eligibility for a client",
        examples=[
            OpenApiExample(
                "Eligibility Request Example",
                value={"client_id": 1},
                request_only=True,
            ),
            OpenApiExample(
                "Eligibility Response Example",
                value={
                    "client_id": 1,
                    "eligible_amount": "7500.00",
                    "details": [
                        {
                            "instrument": "AAPL",
                            "quantity": "100.0000",
                            "avg_price": "150.00",
                            "margin_rate": "0.50",
                            "eligible": "7500.00",
                        }
                    ],
                },
                response_only=True,
            ),
        ],
    )
    @action(detail=False, methods=["post"], url_path="loan-eligibility")
    def loan_eligibility(self, request):
        client_id = request.data.get("client_id")
        if not client_id:
            return Response({"error": "client_id is required"}, status=400)

        portfolios = Portfolio.objects.filter(client_id=client_id).select_related("instrument")
        if not portfolios.exists():
            return Response({"client_id": client_id, "eligible_amount": "0.00", "details": []})

        total_eligible = 0
        details = []
        for p in portfolios:
            if p.instrument.is_marginable:
                eligible = float(p.quantity) * float(p.avg_price) * float(p.instrument.margin_rate)
                total_eligible += eligible
                details.append(
                    {
                        "instrument": p.instrument.symbol,
                        "quantity": str(p.quantity),
                        "avg_price": str(p.avg_price),
                        "margin_rate": str(p.instrument.margin_rate),
                        "eligible": f"{eligible:.2f}",
                    }
                )

        return Response(
            {"client_id": client_id, "eligible_amount": f"{total_eligible:.2f}", "details": details}
        )
        
     # --- new force-sell endpoint ---
    @extend_schema(
        tags=["Broker Actions"],
        description="Force sell client positions if loan exceeds eligibility",
        examples=[
            OpenApiExample(
                "Force Sell Request",
                value={"client_id": 1},
                request_only=True,
            ),
            OpenApiExample(
                "Force Sell Response",
                value={
                    "client_id": 1,
                    "status": "force-sell executed",
                    "sold_positions": [
                        {"instrument": "AAPL", "quantity_sold": "50.0000", "reason": "loan exceeds eligibility"}
                    ],
                },
                response_only=True,
            ),
        ],
    )
    @action(detail=False, methods=["post"], url_path="force-sell")
    def force_sell(self, request):
        client_id = request.data.get("client_id")
        if not client_id:
            return Response({"error": "client_id is required"}, status=400)

        loan = MarginLoan.objects.filter(client_id=client_id).last()
        if not loan:
            return Response({"client_id": client_id, "status": "no active loan"})

        # calculate eligibility again
        portfolios = Portfolio.objects.filter(client_id=client_id).select_related("instrument")
        eligible = 0
        for p in portfolios:
            if p.instrument.is_marginable:
                eligible += float(p.quantity) * float(p.avg_price) * float(p.instrument.margin_rate)

        sold_positions = []
        if loan.loan_amount > eligible:
            excess = float(loan.loan_amount) - eligible
            with transaction.atomic():
                for p in portfolios:
                    if p.instrument.is_marginable and excess > 0 and p.quantity > 0:
                        sell_qty = min(p.quantity, excess / float(p.avg_price))
                        if sell_qty > 0:
                            p.quantity -= sell_qty
                            p.save()
                            sold_positions.append(
                                {
                                    "instrument": p.instrument.symbol,
                                    "quantity_sold": f"{sell_qty:.4f}",
                                    "reason": "loan exceeds eligibility",
                                }
                            )
                            excess -= float(sell_qty) * float(p.avg_price)

                # log the event
                AuditLog.objects.create(
                    event_type="FORCE_SELL",
                    client_id=client_id,
                    loan=loan,
                    details={"sold_positions": sold_positions},
                )

            return Response({"client_id": client_id, "status": "force-sell executed", "sold_positions": sold_positions})

        return Response({"client_id": client_id, "status": "no action needed"})


@extend_schema(
    tags=["Margin Loans"],
    description="Apply, view, and manage margin loans",
    examples=[
        OpenApiExample(
            "Loan Request Example",
            value={"client": 1, "loan_amount": "5000.0000", "interest_rate": "0.08"},
            request_only=True,
        ),
        OpenApiExample(
            "Loan Response Example",
            value={
                "id": 1,
                "client": 1,
                "loan_amount": "5000.0000",
                "interest_rate": "0.08",
                "created_at": "2025-09-07T10:30:00Z",
                "updated_at": "2025-09-07T10:30:00Z",
            },
            response_only=True,
        ),
    ],
)    
class MarginLoanViewSet(viewsets.ModelViewSet):
    queryset = MarginLoan.objects.all()
    serializer_class = MarginLoanSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        loan = serializer.save()

        # 1️⃣ Publish Kafka event
        KafkaProducerWrapper.send_event(
            topic="margin-loan-events",
            key=str(loan.client.id),
            event={
                "type": "LOAN_CREATED",
                "loan_id": loan.id,
                "client_id": loan.client.id,
                "amount": str(loan.loan_amount),
                "interest_rate": str(loan.interest_rate),
                "created_at": str(loan.created_at),
            },
        )

        # 2️⃣ Audit log
        AuditLog.objects.create(
            event_type="LOAN_CREATED",
            client=loan.client,
            loan=loan,
            details={"amount": str(loan.loan_amount)},
        )

        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
    
    
class AuditLogViewSet(viewsets.ModelViewSet):   # 🔹 New
    queryset = AuditLog.objects.all()
    serializer_class = AuditLogSerializer