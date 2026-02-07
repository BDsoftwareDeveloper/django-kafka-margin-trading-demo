from decimal import Decimal

BOARD_LEVERAGE = {
    "A": Decimal("1.50"),
    "B": Decimal("1.25"),
    "Z": Decimal("0.00"),
}
UTILIZATION_LEVELS = {
    "SAFE": Decimal("70"),
    "WARNING": Decimal("85"),
    "MARGIN_CALL": Decimal("95"),
    "FORCE_SELL": Decimal("100"),
}