from decimal import Decimal
from django.test import TestCase

from core.models import Client, Instrument, Portfolio
from risk.models import ClientRiskProfile
from risk.services.risk_engine import RiskEngine, RiskViolation
from risk.constants import UTILIZATION_LEVELS

class RiskEngineBaseTest(TestCase):
    def setUp(self):
        self.client_obj = Client.objects.create(
            name="Test Client",
            email="test@example.com",
            cash_balance=Decimal("100000.00"),
        )

        self.risk = ClientRiskProfile.objects.create(
            client=self.client_obj,
            allow_margin=True,
            leverage_multiplier=Decimal("1.50"),
        )
        self.risk.recalculate()

        self.a_board = Instrument.objects.create(
            symbol="AAPL",
            name="Apple",
            exchange="NASDAQ",
            board="A",
            is_marginable=True,
            margin_rate=Decimal("0.50"),
        )

        self.b_board = Instrument.objects.create(
            symbol="BTEST",
            name="B Board",
            exchange="DSE",
            board="B",
            is_marginable=True,
            margin_rate=Decimal("0.50"),
        )

        self.z_board = Instrument.objects.create(
            symbol="ZBAD",
            name="Z Board",
            exchange="DSE",
            board="Z",
            is_marginable=True,
            margin_rate=Decimal("0.50"),
        )


class TestExposureCalculation(RiskEngineBaseTest):

    def test_used_exposure_calculation(self):
        Portfolio.objects.create(
            client=self.client_obj,
            instrument=self.a_board,
            quantity=Decimal("100"),
            avg_price=Decimal("1000"),
        )

        used = RiskEngine.calculate_current_exposure(self.client_obj.id)

        # A-board → 50% margin
        expected = Decimal("100000") * Decimal("0.50")
        self.assertEqual(used, expected)


class TestZBoardRules(RiskEngineBaseTest):

    def test_z_board_margin_block(self):
        with self.assertRaises(RiskViolation):
            RiskEngine.check_pre_trade(
                client_id=self.client_obj.id,
                instrument=self.z_board,
                side="BUY",
                quantity=Decimal("10"),
                price=Decimal("100"),
                is_margin=True,
            )


class TestMarginDisabled(RiskEngineBaseTest):

    def test_margin_disabled_blocks_trade(self):
        self.risk.allow_margin = False
        self.risk.save()

        with self.assertRaises(RiskViolation):
            RiskEngine.check_pre_trade(
                client_id=self.client_obj.id,
                instrument=self.a_board,
                side="BUY",
                quantity=Decimal("10"),
                price=Decimal("100"),
                is_margin=True,
            )

class TestEDRCalculation(RiskEngineBaseTest):

    def test_margin_utilization(self):
        Portfolio.objects.create(
            client=self.client_obj,
            instrument=self.a_board,
            quantity=Decimal("50"),
            avg_price=Decimal("1000"),
        )

        utilization = RiskEngine.margin_utilization(self.client_obj.id)

        # Used = 50 × 1000 × 0.5 = 25,000
        # Max = 100,000 × 1.5 = 150,000
        expected = (Decimal("25000") / Decimal("150000")) * Decimal("100")

        self.assertEqual(
            utilization.quantize(Decimal("0.01")),
            expected.quantize(Decimal("0.01")),
        )
class TestForceSellLogic(RiskEngineBaseTest):

    def test_force_sell_disables_margin(self):
        # Push exposure above FORCE_SELL
        Portfolio.objects.create(
            client=self.client_obj,
            instrument=self.a_board,
            quantity=Decimal("300"),
            avg_price=Decimal("1000"),
        )

        RiskEngine.enforce_margin_policy(self.client_obj.id)

        self.risk.refresh_from_db()
        self.assertFalse(self.risk.allow_margin)
class TestMarginReEnable(RiskEngineBaseTest):

    def test_margin_reenabled_when_safe(self):
        self.risk.allow_margin = False
        self.risk.save()

        # Low exposure
        Portfolio.objects.create(
            client=self.client_obj,
            instrument=self.a_board,
            quantity=Decimal("10"),
            avg_price=Decimal("100"),
        )

        RiskEngine.enforce_margin_policy(self.client_obj.id)

        self.risk.refresh_from_db()
        self.assertTrue(self.risk.allow_margin)
class TestLoanAmount(RiskEngineBaseTest):

    def test_loan_amount_computation(self):
        Portfolio.objects.create(
            client=self.client_obj,
            instrument=self.a_board,
            quantity=Decimal("100"),
            avg_price=Decimal("1000"),
        )

        loan = RiskEngine.loan_amount(self.client_obj.id)

        # Used = 50,000
        # Cash = 100,000
        self.assertEqual(loan, Decimal("0.00"))
