from decimal import Decimal
from core.models import Portfolio

def apply_trade(client, instrument, qty, price):
    portfolio, _ = Portfolio.objects.get_or_create(
        client=client,
        instrument=instrument,
        defaults={"quantity": Decimal("0"), "avg_price": Decimal("0")}
    )

    total_cost = portfolio.quantity * portfolio.avg_price
    trade_cost = qty * price

    new_qty = portfolio.quantity + qty
    if new_qty <= 0:
        portfolio.delete()
        return None

    portfolio.avg_price = (total_cost + trade_cost) / new_qty
    portfolio.quantity = new_qty
    portfolio.save()
    return portfolio
