from decimal import Decimal, ROUND_HALF_UP
from core.models import Client, Portfolio, Instrument, AuditLog, MarginLoan
from django.db import transaction
from risk.models import ClientRiskProfile
from risk.constants import BOARD_LEVERAGE, UTILIZATION_LEVELS


class RiskViolation(Exception):
    pass


class RiskEngine:
    
    
    
    # ------------------------------
    # LOAN CALCULATION
    # ------------------------------
    @staticmethod
    def loan_amount(client_id: int) -> Decimal:
        """
        Loan = max(0, Used Exposure − Cash Balance)
        """
        client = Client.objects.get(id=client_id)

        used = RiskEngine.calculate_current_exposure(client_id)
        cash = client.cash_balance or Decimal("0.00")

        loan = used - cash
        if loan < 0:
            loan = Decimal("0.00")

        return loan.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    # ------------------------------
    # EXPOSURE CALCULATION
    # ------------------------------
        
    @staticmethod
    def calculate_current_exposure(client_id: int) -> Decimal:
        """
        Used Exposure =
        Σ(position_value × min(board_rate, client_leverage))
        """

        exposure = Decimal("0.00")

        profile = ClientRiskProfile.objects.get(client_id=client_id)

        portfolios = (
            Portfolio.objects
            .select_related("instrument")
            .filter(client_id=client_id)
        )

        for p in portfolios:
            instrument = p.instrument
            rate = instrument.effective_margin_rate()

            # ❌ Non-marginable or Z-board
            if rate <= 0:
                continue

            effective_rate = min(rate, profile.leverage_multiplier)

            exposure += p.quantity * p.avg_price * effective_rate

        return exposure.quantize(Decimal("0.01"), ROUND_HALF_UP)

    @staticmethod
    def available_exposure(client_id: int) -> Decimal:
        profile = ClientRiskProfile.objects.get(client_id=client_id)
        used = RiskEngine.calculate_current_exposure(client_id)

        return max(
            Decimal("0.00"),
            (profile.max_exposure - used).quantize(Decimal("0.01"))
        )


    # ------------------------------
    # PRE-TRADE (HARD RULES)
    # ------------------------------
    @staticmethod
    def check_pre_trade(
        *,
        client_id: int,
        instrument: Instrument,
        side: str,
        quantity: Decimal,
        price: Decimal,
        is_margin: bool,
    ):
        side = side.upper()

        # ✅ SELL always allowed
        if side == "SELL":
            return

        profile = ClientRiskProfile.objects.get(client_id=client_id)

        # --- RULE 1: client margin disabled ---
        if is_margin and not profile.allow_margin:
            raise RiskViolation(
                "Margin disabled due to FORCE SELL"
            )

        # --- RULE 2: instrument marginable ---
        if is_margin and not instrument.is_marginable:
            raise RiskViolation(
                f"{instrument.symbol} is not marginable"
            )

        # --- RULE 3: Z-board hard block ---
        if is_margin and instrument.board == "Z":
            raise RiskViolation(
                f"{instrument.symbol} (Z-board) cannot be bought on margin"
            )

        # --- RULE 4: effective rate ---
        rate = instrument.effective_margin_rate()
        effective_rate = min(rate, profile.leverage_multiplier)

        if effective_rate <= 0:
            raise RiskViolation("Margin rate is zero")

        # --- RULE 5: exposure availability ---
        trade_value = (quantity * price).quantize(Decimal("0.01"))
        required = (trade_value * effective_rate).quantize(Decimal("0.01"))

        available = RiskEngine.available_exposure(client_id)

        if required > available:
            raise RiskViolation(
                f"Exposure exceeded. Required={required}, Available={available}"
            )




    @staticmethod
    @transaction.atomic
    def sync_margin_loan(client_id: int):
        """
        Auto-create / update / close MarginLoan
        based on (Used Exposure − Cash)
        """
        loan_amount = RiskEngine.loan_amount(client_id)

        loan = (
            MarginLoan.objects
            .filter(client_id=client_id)
            .order_by("-created_at")
            .first()
        )

        # -----------------------
        # CASE 1: loan required
        # -----------------------
        if loan_amount > 0:
            if loan:
                if loan.loan_amount != loan_amount:
                    loan.loan_amount = loan_amount
                    loan.save(update_fields=["loan_amount", "updated_at"])

                    AuditLog.log_event(
                        event_type="MARGIN_LOAN_UPDATED",
                        client=loan.client,
                        loan=loan,
                        details={"loan_amount": str(loan_amount)},
                    )
            else:
                loan = MarginLoan.objects.create(
                    client_id=client_id,
                    loan_amount=loan_amount,
                )

                AuditLog.log_event(
                    event_type="MARGIN_LOAN_CREATED",
                    client=loan.client,
                    loan=loan,
                    details={"loan_amount": str(loan_amount)},
                )

            return loan

        # -----------------------
        # CASE 2: loan not needed
        # -----------------------
        if loan:
            AuditLog.log_event(
                event_type="MARGIN_LOAN_CLOSED",
                client=loan.client,
                loan=loan,
                details={"reason": "Cash covers exposure"},
            )
            loan.delete()

        return None
    # ------------------------------
    # POST-TRADE / MTM
    # ------------------------------
    @staticmethod
    def enforce_post_trade(client_id):
        """
        Post-trade / MTM / policy enforcement
        """
        profile = ClientRiskProfile.objects.get(client_id=client_id)
        used = RiskEngine.calculate_current_exposure(client_id)

        if used > profile.max_exposure:
            RiskEngine.enforce_margin_policy(client_id)

            raise RiskViolation(
                f"Exposure breach: {used} > {profile.max_exposure}"
            )

    # ------------------------------
    # MARGIN POLICY ENFORCEMENT
    # ------------------------------

    @staticmethod
    def enforce_margin_policy(client_id: int):
        """
        Margin enable/disable + loan sync
        """
        profile = ClientRiskProfile.objects.select_related("client").get(
            client_id=client_id
        )

        if profile.max_exposure == 0:
            return

        used = RiskEngine.calculate_current_exposure(client_id)
        utilization = (used / profile.max_exposure) * Decimal("100")

        # 🔁 ALWAYS sync loan
        RiskEngine.sync_margin_loan(client_id)

        # ---------------- FORCE SELL / MARGIN CALL ----------------
        if utilization >= UTILIZATION_LEVELS["MARGIN_CALL"]:
            if profile.allow_margin:
                profile.allow_margin = False
                profile.save(update_fields=["allow_margin"])

                AuditLog.log_event(
                    event_type="MARGIN_DISABLED",
                    client=profile.client,
                    details={
                        "utilization": str(utilization),
                        "used": str(used),
                    },
                )
            return

        # ---------------- SAFE ZONE ----------------
        if not profile.allow_margin:
            profile.allow_margin = True
            profile.save(update_fields=["allow_margin"])

            AuditLog.log_event(
                event_type="MARGIN_RE_ENABLED",
                client=profile.client,
                details={
                    "utilization": str(utilization),
                    "used": str(used),
                },
            )


        
    # ------------------------------
    # UTILIZATION / EDR
    # ------------------------------
    # ==============================
    # UTILIZATION / EDR
    # ==============================

    @staticmethod
    def margin_utilization(client_id: int) -> Decimal:
        profile = ClientRiskProfile.objects.get(client_id=client_id)

        if profile.max_exposure == 0:
            return Decimal("0.00")

        used = RiskEngine.calculate_current_exposure(client_id)
        return (
            (used / profile.max_exposure) * Decimal("100")
        ).quantize(Decimal("0.01"))

    @staticmethod
    def utilization_status(client_id: int) -> str:
        u = RiskEngine.margin_utilization(client_id)

        if u < UTILIZATION_LEVELS["SAFE"]:
            return "SAFE"
        elif u < UTILIZATION_LEVELS["WARNING"]:
            return "WARNING"
        elif u < UTILIZATION_LEVELS["MARGIN_CALL"]:
            return "MARGIN_CALL"
        return "FORCE_SELL"
