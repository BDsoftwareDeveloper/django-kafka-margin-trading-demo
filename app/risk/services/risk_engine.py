from decimal import Decimal, ROUND_HALF_UP
from core.models import Portfolio, Instrument, AuditLog
from risk.models import ClientRiskProfile
from risk.constants import BOARD_LEVERAGE, UTILIZATION_LEVELS


class RiskViolation(Exception):
    pass


class RiskEngine:
    # ------------------------------
    # EXPOSURE CALCULATION
    # ------------------------------
        
    @staticmethod
    def calculate_current_exposure(client_id):
        """
        Used Exposure =
        Σ(position_value × effective_leverage)
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

            # ❌ Not marginable or Z-board
            rate = instrument.effective_margin_rate()
            if rate == 0:
                continue

            # 🔒 Apply client leverage cap
            effective_rate = min(rate, profile.leverage_multiplier)

            position_value = p.quantity * p.avg_price
            exposure += position_value * effective_rate

        return exposure.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @staticmethod
    def available_exposure(client_id: int) -> Decimal:
        profile = ClientRiskProfile.objects.get(client_id=client_id)
        used = RiskEngine.calculate_current_exposure(client_id)

        return (profile.max_exposure - used).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
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
        """
        HARD BLOCKS before order placement
        Exchange-grade pre-trade risk validation
        """

        side = side.upper()

        # ✅ SELL is always allowed (risk reducing)
        if side == "SELL":
            return

        profile = ClientRiskProfile.objects.get(client_id=client_id)

        # --- RULE 1: margin disabled at client level ---
        if is_margin and not profile.allow_margin:
            raise RiskViolation(
                "Margin trading disabled due to risk breach (FORCE SELL)"
            )

        # --- RULE 2: instrument must be marginable ---
        if is_margin and not instrument.is_marginable:
            raise RiskViolation(
                f"Instrument '{instrument.symbol}' is not marginable"
            )

        # --- RULE 3: Z-board hard block ---
        if is_margin and instrument.board == "Z":
            raise RiskViolation(
                f"Z-board instrument '{instrument.symbol}' cannot be bought on margin"
            )

        # --- RULE 4: effective margin rate check ---
        rate = instrument.effective_margin_rate()
        if is_margin and rate <= Decimal("0.00"):
            raise RiskViolation(
                f"Margin not allowed for instrument '{instrument.symbol}' "
                f"(board={instrument.board})"
            )

        # --- RULE 5: exposure availability ---
        trade_value = (quantity * price).quantize(Decimal("0.01"))
        required = (trade_value * rate).quantize(Decimal("0.01"))

        available = RiskEngine.available_exposure(client_id)

        if available <= Decimal("0.00"):
            raise RiskViolation("No margin exposure available")

        if required > available:
            raise RiskViolation(
                f"Exposure exceeded. Required={required}, Available={available}"
            )


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
        Enforces margin enable/disable based on EDR%
        """
        profile = ClientRiskProfile.objects.select_related("client").get(
            client_id=client_id
        )

        if profile.max_exposure == 0:
            return

        used = RiskEngine.calculate_current_exposure(client_id)
        utilization = (used / profile.max_exposure) * Decimal("100")

        # --- FORCE SELL ---
        if utilization >= UTILIZATION_LEVELS["FORCE_SELL"]:
            if profile.allow_margin:
                profile.allow_margin = False
                profile.save(update_fields=["allow_margin"])

                from core.models import AuditLog
                AuditLog.log_event(
                    event_type="FORCE_SELL_MARGIN_DISABLED",
                    client=profile.client,
                    details={
                        "used": str(used),
                        "max": str(profile.max_exposure),
                        "utilization": str(utilization),
                    },
                )
            return

        # --- SAFE / WARNING / MARGIN_CALL ---
        if not profile.allow_margin:
            profile.allow_margin = True
            profile.save(update_fields=["allow_margin"])

            from core.models import AuditLog
            AuditLog.log_event(
                event_type="MARGIN_RE_ENABLED",
                client=profile.client,
                details={
                    "used": str(used),
                    "max": str(profile.max_exposure),
                    "utilization": str(utilization),
                },
            )
        
    # ------------------------------
    # UTILIZATION / EDR
    # ------------------------------
    @staticmethod
    def margin_utilization(client_id: int) -> Decimal:
        profile = ClientRiskProfile.objects.get(client_id=client_id)

        if profile.max_exposure == 0:
            return Decimal("0.00")

        used = RiskEngine.calculate_current_exposure(client_id)
        utilization = (used / profile.max_exposure) * Decimal("100")

        return utilization.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @staticmethod
    def utilization_status(client_id: int) -> str:
        utilization = RiskEngine.margin_utilization(client_id)

        if utilization < UTILIZATION_LEVELS["SAFE"]:
            return "SAFE"
        elif utilization < UTILIZATION_LEVELS["WARNING"]:
            return "WARNING"
        elif utilization < UTILIZATION_LEVELS["MARGIN_CALL"]:
            return "MARGIN_CALL"
        else:
            return "FORCE_SELL"
