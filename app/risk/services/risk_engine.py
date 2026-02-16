from decimal import Decimal, ROUND_HALF_UP
from django.db import transaction
from django.utils import timezone

from core.models import (
    Client,
    Portfolio,
    MarginLoan,
    AuditLog,
    MarketPrice,
)

from risk.models import ClientRiskProfile


class RiskViolation(Exception):
    pass


class RiskEngine:

    # ==========================================================
    # 1️⃣ EQUITY SNAPSHOT (REAL-TIME MTM)
    # ==========================================================
    @staticmethod
    def equity_snapshot(client_id: int) -> dict:
        """
        Institutional equity-based margin calculation.

        Market Value = Σ(qty × mark_price)
        Loan = Active principal + accrued interest
        Net Equity = Market Value − Loan
        Maintenance Requirement = Σ(MV × maintenance_rate)
        Margin Level = (Net Equity / Maintenance) × 100
        """

        client = Client.objects.get(id=client_id)

        portfolios = (
            Portfolio.objects
            .select_related("instrument__market_price")
            .filter(client_id=client_id)
        )

        total_market_value = Decimal("0.00")
        maintenance_requirement = Decimal("0.00")

        for p in portfolios:
            try:
                price = p.instrument.market_price.last_price
            except MarketPrice.DoesNotExist:
                continue

            position_value = p.quantity * price
            total_market_value += position_value

            maintenance_requirement += (
                position_value * p.instrument.maintenance_margin_rate
            )

        total_market_value = total_market_value.quantize(Decimal("0.01"))
        maintenance_requirement = maintenance_requirement.quantize(Decimal("0.01"))

        loan = RiskEngine.loan_amount(client_id)

        net_equity = (total_market_value - loan).quantize(Decimal("0.01"))

        if maintenance_requirement == 0:
            margin_level = Decimal("999.99")
        else:
            margin_level = (
                (net_equity / maintenance_requirement) * Decimal("100")
            ).quantize(Decimal("0.01"))

        return {
            "market_value": total_market_value,
            "loan": loan,
            "net_equity": net_equity,
            "maintenance_requirement": maintenance_requirement,
            "margin_level_percent": margin_level,
        }

    # ==========================================================
    # 2️⃣ LOAN LEDGER VALUE
    # ==========================================================
    @staticmethod
    def loan_amount(client_id: int) -> Decimal:
        """
        Returns active loan principal + accrued interest.
        Independent from market value.
        """

        loan = (
            MarginLoan.objects
            .filter(client_id=client_id, status="ACTIVE")
            .first()
        )

        if not loan:
            return Decimal("0.00")

        return (
            loan.principal_amount + loan.accrued_interest
        ).quantize(Decimal("0.01"))

    # ==========================================================
    # 3️⃣ MARGIN STATUS ENGINE
    # ==========================================================
    @staticmethod
    def evaluate_margin_status(client_id: int) -> str:
        """
        Determines SAFE / WARNING / MARGIN_CALL / FORCE_SELL
        based on equity margin level thresholds.
        """

        profile = ClientRiskProfile.objects.select_related("client").get(
            client_id=client_id
        )

        snapshot = RiskEngine.equity_snapshot(client_id)
        margin_level = snapshot["margin_level_percent"]

        if margin_level >= profile.warning_level:
            status = "SAFE"
        elif margin_level >= profile.margin_call_level:
            status = "WARNING"
        elif margin_level >= profile.force_sell_level:
            status = "MARGIN_CALL"
        else:
            status = "FORCE_SELL"

        profile.current_status = status
        profile.allow_margin = status in ["SAFE", "WARNING"]
        profile.save(update_fields=["current_status", "allow_margin"])

        if status == "FORCE_SELL":
            RiskEngine.auto_liquidate(client_id)

        return status

    # ==========================================================
    # 4️⃣ AUTO LIQUIDATION (CONTROLLED)
    # ==========================================================
    @staticmethod
    @transaction.atomic
    def auto_liquidate(client_id: int):
        """
        Gradually liquidate positions until margin level
        reaches margin_call_level threshold.
        """

        profile = ClientRiskProfile.objects.get(client_id=client_id)
        target_level = profile.margin_call_level

        portfolios = (
            Portfolio.objects
            .select_related("instrument__market_price")
            .filter(client_id=client_id)
            .order_by("-quantity")
        )

        for p in portfolios:

            try:
                price = p.instrument.market_price.last_price
            except MarketPrice.DoesNotExist:
                continue

            if p.quantity <= 0:
                continue

            snapshot = RiskEngine.equity_snapshot(client_id)

            if snapshot["margin_level_percent"] >= target_level:
                break

            maintenance_rate = p.instrument.maintenance_margin_rate

            required_equity = (
                snapshot["maintenance_requirement"]
                - snapshot["net_equity"]
            )

            if required_equity <= 0:
                break

            qty_to_sell = (
                required_equity / (price * maintenance_rate)
            ).quantize(Decimal("0.0001"), ROUND_HALF_UP)

            qty_to_sell = min(qty_to_sell, p.quantity)

            p.quantity -= qty_to_sell
            p.save(update_fields=["quantity"])

            AuditLog.log_event(
                event_type="AUTO_LIQUIDATION_EXECUTED",
                client=p.client,
                details={
                    "instrument": p.instrument.symbol,
                    "quantity_sold": str(qty_to_sell),
                },
            )

    # ==========================================================
    # 5️⃣ POST-TRADE ENFORCEMENT
    # ==========================================================
    @staticmethod
    def enforce_post_trade(client_id: int):
        """
        Called after every trade.
        """

        RiskEngine.evaluate_margin_status(client_id)

    # ==========================================================
    # 6️⃣ DAILY INTEREST ACCRUAL
    # ==========================================================
    @staticmethod
    @transaction.atomic
    def accrue_daily_interest(client_id: int):

        loan = (
            MarginLoan.objects
            .select_for_update()
            .filter(client_id=client_id, status="ACTIVE")
            .first()
        )

        if not loan:
            return

        daily_rate = loan.interest_rate / Decimal("365")

        interest = (
            loan.principal_amount * daily_rate
        ).quantize(Decimal("0.01"), ROUND_HALF_UP)

        loan.accrued_interest += interest
        loan.save(update_fields=["accrued_interest"])

        AuditLog.log_event(
            event_type="INTEREST_ACCRUED",
            client=loan.client,
            details={"interest": str(interest)},
        )
