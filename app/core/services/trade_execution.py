from decimal import Decimal, ROUND_HALF_UP
from django.db import transaction
from django.utils import timezone

from core.models import Client, Portfolio, MarginLoan, AuditLog
from risk.services.risk_engine import RiskEngine


class TradeExecutionService:

    @staticmethod
    @transaction.atomic
    def execute_trade(
        *,
        client_id: int,
        instrument,
        side: str,
        quantity: Decimal,
        price: Decimal,
    ):
        """
        Institutional Broker-Grade Trade Execution

        ✔ Portfolio update
        ✔ Automatic loan increase on margin BUY
        ✔ Interest-first repayment on SELL
        ✔ Principal preserved (ledger integrity)
        ✔ Single ACTIVE loan per client
        ✔ Fully atomic execution
        ✔ Post-trade risk enforcement
        """

        side = side.upper()

        client = Client.objects.select_for_update().get(id=client_id)

        trade_value = (quantity * price).quantize(
            Decimal("0.01"), ROUND_HALF_UP
        )

        portfolio, _ = Portfolio.objects.select_for_update().get_or_create(
            client_id=client_id,
            instrument=instrument,
            defaults={
                "quantity": Decimal("0.0000"),
                "avg_price": Decimal("0.0000"),
            },
        )

        # =====================================================
        # BUY FLOW
        # =====================================================
        if side == "BUY":

            available_cash = (
                client.cash_balance - client.blocked_cash
            ).quantize(Decimal("0.01"))

            if trade_value <= available_cash:
                # Pure cash trade
                client.cash_balance -= trade_value

            else:
                # Margin required
                cash_used = max(Decimal("0.00"), available_cash)
                borrow_amount = trade_value - cash_used

                client.cash_balance = max(
                    Decimal("0.00"),
                    client.cash_balance - cash_used
                )

                loan = (
                    MarginLoan.objects
                    .select_for_update()
                    .filter(client=client, status="ACTIVE")
                    .first()
                )

                if loan:
                    loan.principal_amount += borrow_amount
                    loan.save(update_fields=["principal_amount"])

                    AuditLog.log_event(
                        event_type="MARGIN_LOAN_INCREASED",
                        client=client,
                        details={"borrowed": str(borrow_amount)},
                    )
                else:
                    loan = MarginLoan.objects.create(
                        client=client,
                        principal_amount=borrow_amount,
                        status="ACTIVE",
                    )

                    AuditLog.log_event(
                        event_type="MARGIN_LOAN_CREATED",
                        client=client,
                        details={"borrowed": str(borrow_amount)},
                    )

            # ---- Update Portfolio (VWAP logic)
            total_cost = (
                portfolio.quantity * portfolio.avg_price
            ) + trade_value

            new_quantity = portfolio.quantity + quantity

            if new_quantity > 0:
                portfolio.avg_price = (
                    total_cost / new_quantity
                ).quantize(Decimal("0.0001"), ROUND_HALF_UP)

            portfolio.quantity = new_quantity

            portfolio.save(update_fields=["quantity", "avg_price"])
            client.save(update_fields=["cash_balance"])

        # =====================================================
        # SELL FLOW
        # =====================================================
        elif side == "SELL":

            if quantity > portfolio.quantity:
                raise Exception("Insufficient shares")

            portfolio.quantity -= quantity
            proceeds = trade_value

            loan = (
                MarginLoan.objects
                .select_for_update()
                .filter(client=client, status="ACTIVE")
                .first()
            )

            if loan:

                # ------------------------------------------------
                # 1️⃣ Repay accrued interest first
                # ------------------------------------------------
                repaid_interest = Decimal("0.00")
                repaid_principal = Decimal("0.00")

                if proceeds >= loan.accrued_interest:
                    repaid_interest = loan.accrued_interest
                    proceeds -= loan.accrued_interest
                    loan.accrued_interest = Decimal("0.00")
                else:
                    repaid_interest = proceeds
                    loan.accrued_interest -= proceeds
                    proceeds = Decimal("0.00")
                    loan.save(update_fields=["accrued_interest"])

                    AuditLog.log_event(
                        event_type="MARGIN_LOAN_PARTIAL_REPAY",
                        client=client,
                        details={
                            "interest_repaid": str(repaid_interest),
                            "principal_repaid": "0.00",
                        },
                    )
                    portfolio.save(update_fields=["quantity"])
                    client.save(update_fields=["cash_balance"])
                    return

                # ------------------------------------------------
                # 2️⃣ Repay principal
                # ------------------------------------------------
                if proceeds >= loan.principal_amount:
                    repaid_principal = loan.principal_amount
                    proceeds -= loan.principal_amount

                    loan.status = "CLOSED"
                    loan.closed_at = timezone.now()
                    loan.save(update_fields=[
                        "principal_amount",
                        "accrued_interest",
                        "status",
                        "closed_at",
                    ])

                    AuditLog.log_event(
                        event_type="MARGIN_LOAN_CLOSED",
                        client=client,
                        details={
                            "interest_repaid": str(repaid_interest),
                            "principal_repaid": str(repaid_principal),
                        },
                    )
                else:
                    repaid_principal = proceeds
                    loan.principal_amount -= proceeds
                    proceeds = Decimal("0.00")

                    loan.save(update_fields=[
                        "principal_amount",
                        "accrued_interest",
                    ])

                    AuditLog.log_event(
                        event_type="MARGIN_LOAN_PARTIAL_REPAY",
                        client=client,
                        details={
                            "interest_repaid": str(repaid_interest),
                            "principal_repaid": str(repaid_principal),
                        },
                    )

            # Remaining proceeds → cash
            client.cash_balance += proceeds

            portfolio.save(update_fields=["quantity"])
            client.save(update_fields=["cash_balance"])

        else:
            raise Exception("Invalid trade side")

        # =====================================================
        # POST-TRADE RISK CHECK
        # =====================================================

        RiskEngine.enforce_post_trade(client_id)

        snapshot = RiskEngine.equity_snapshot(client_id)

        if snapshot["net_equity"] < 0:
            raise Exception("Negative equity detected — trade invalid")

        AuditLog.log_event(
            event_type="TRADE_EXECUTED",
            client=client,
            details={
                "side": side,
                "quantity": str(quantity),
                "price": str(price),
            },
        )
