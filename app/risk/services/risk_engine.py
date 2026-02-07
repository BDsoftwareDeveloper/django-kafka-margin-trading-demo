
from decimal import Decimal, ROUND_HALF_UP
from core.models import Portfolio, Instrument
from risk.models import ClientRiskProfile
from risk.constants import BOARD_LEVERAGE
from risk.constants import UTILIZATION_LEVELS


class RiskViolation(Exception):
    pass


class RiskEngine:
    @staticmethod
    def _position_exposure(p):
        """
        Margin exposure for a single position
        """
        instrument = p.instrument
        profile = p.client.clientriskprofile

        # Margin disabled at client level
        if not profile.allow_margin:
            return Decimal("0.00")

        # Instrument not marginable
        if not instrument.is_marginable:
            return Decimal("0.00")

        board_leverage = BOARD_LEVERAGE.get(instrument.board, Decimal("0.00"))

        # Z board or blocked
        if board_leverage == 0:
            return Decimal("0.00")

        effective_leverage = min(
            profile.leverage_multiplier,
            board_leverage,
        )

        position_value = p.quantity * p.avg_price
        return position_value * effective_leverage

    # @staticmethod
    # def calculate_current_exposure(client_id):
    #     """
    #     Σ(board-wise leveraged position exposure)
    #     """
    #     exposure = Decimal("0.00")

    #     qs = (
    #         Portfolio.objects
    #         .filter(client_id=client_id)
    #         .select_related("instrument", "client__clientriskprofile")
    #     )

    #     for p in qs:
    #         exposure += RiskEngine._position_exposure(p)

    #     return exposure
    @staticmethod
    def calculate_current_exposure(client_id):
        """
        Exposure = Σ(qty × price × effective_margin_rate)
        """
        exposure = Decimal("0.00")

        portfolios = Portfolio.objects.select_related("instrument").filter(
            client_id=client_id
        )

        for p in portfolios:
            rate = p.instrument.effective_margin_rate()
            exposure += p.quantity * p.avg_price * rate

        return exposure.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @staticmethod
    def available_exposure(client_id):
        profile = ClientRiskProfile.objects.get(client_id=client_id)
        used = RiskEngine.calculate_current_exposure(client_id)
        return (profile.max_exposure - used).quantize(Decimal("0.01"))

    @staticmethod
    def check_new_trade(client_id, trade_value, instrument):
        """
        Pre-trade risk check
        """
        profile = ClientRiskProfile.objects.get(client_id=client_id)

        if not profile.allow_margin:
            raise RiskViolation("Margin trading disabled for client")

        board_leverage = BOARD_LEVERAGE.get(instrument.board, Decimal("0.00"))
        if board_leverage == 0:
            raise RiskViolation(f"{instrument.symbol} not allowed for margin (Z board)")

        effective_leverage = min(profile.leverage_multiplier, board_leverage)

        required_exposure = trade_value * effective_leverage
        available = RiskEngine.available_exposure(client_id)

        if required_exposure > available:
            raise RiskViolation(
                f"Exposure exceeded. Required={required_exposure}, Available={available}"
            )

    @staticmethod
    def enforce_post_trade(client_id):
        """
        Post-trade / MTM / policy enforcement
        """
        profile = ClientRiskProfile.objects.get(client_id=client_id)
        used = RiskEngine.calculate_current_exposure(client_id)

        if used > profile.max_exposure:
            raise RiskViolation(
                f"Exposure breach: {used} > {profile.max_exposure}"
            )

    
    @staticmethod
    def margin_utilization(client_id):
        profile = ClientRiskProfile.objects.get(client_id=client_id)

        if profile.max_exposure == 0:
            return Decimal("0.00")

        used = RiskEngine.calculate_current_exposure(client_id)
        utilization = (used / profile.max_exposure) * Decimal("100")

        return utilization.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @staticmethod
    def utilization_status(client_id):
        utilization = RiskEngine.margin_utilization(client_id)

        if utilization < UTILIZATION_LEVELS["SAFE"]:
            return "SAFE"
        elif utilization < UTILIZATION_LEVELS["WARNING"]:
            return "WARNING"
        elif utilization < UTILIZATION_LEVELS["MARGIN_CALL"]:
            return "MARGIN_CALL"
        else:
            return "FORCE_SELL"
        
        
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
        Pre-trade risk checks (HARD rules)
        """

        # --- RULE 1: Z-board + margin BUY is forbidden ---
        if (
            side.upper() == "BUY"
            and instrument.board == "Z"
            and is_margin
        ):
            raise RiskViolation(
                f"Z-board instrument '{instrument.symbol}' "
                f"cannot be bought on margin"
            )

        # --- RULE 2: margin disabled for client ---
        profile = ClientRiskProfile.objects.get(client_id=client_id)
        if is_margin and not profile.allow_margin:
            raise RiskViolation("Margin trading is disabled for this client")