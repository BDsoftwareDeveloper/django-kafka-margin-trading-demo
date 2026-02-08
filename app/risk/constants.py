# from decimal import Decimal

# BOARD_LEVERAGE = {
#     "A": Decimal("1.50"),
#     "B": Decimal("1.25"),
#     "Z": Decimal("0.00"),
# }
# UTILIZATION_LEVELS = {
#     "SAFE": Decimal("70"),
#     "WARNING": Decimal("85"),
#     "MARGIN_CALL": Decimal("95"),
#     "FORCE_SELL": Decimal("100"),
# }

# risk/constants.py
from decimal import Decimal

BOARD_LEVERAGE = {
    "A": Decimal("1.00"),
    "B": Decimal("0.75"),
    "Z": Decimal("0.00"),
}

# % utilization thresholds
UTILIZATION_LEVELS = {
    "SAFE": Decimal("50.00"),         # < 50%
    "WARNING": Decimal("70.00"),      # 50–70%
    "MARGIN_CALL": Decimal("85.00"),  # 70–85%
    "FORCE_SELL": Decimal("100.00"),  # >= 100%
}
