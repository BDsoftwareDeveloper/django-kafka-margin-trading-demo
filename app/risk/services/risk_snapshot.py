# risk/services/risk_snapshot.py

from dataclasses import dataclass
from decimal import Decimal


@dataclass
class RiskSnapshot:
    client_id: int

    market_value: Decimal
    margin_value: Decimal
    used_exposure: Decimal

    equity: Decimal
    loan_amount: Decimal

    max_exposure: Decimal
    available_exposure: Decimal

    utilization_percent: Decimal
    status: str
