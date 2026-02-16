from decimal import Decimal
from django.db.models import Sum
from core.models import Client, MarginLoan, Portfolio


class HouseRiskService:

    @staticmethod
    def snapshot():

        total_principal = (
            MarginLoan.objects
            .filter(status="ACTIVE")
            .aggregate(total=Sum("principal_amount"))["total"]
            or Decimal("0.00")
        )

        total_interest = (
            MarginLoan.objects
            .filter(status="ACTIVE")
            .aggregate(total=Sum("accrued_interest"))["total"]
            or Decimal("0.00")
        )

        total_market_value = Decimal("0.00")
        maintenance_requirement = Decimal("0.00")

        portfolios = Portfolio.objects.select_related(
            "instrument__market_price"
        )

        for p in portfolios:
            try:
                price = p.instrument.market_price.last_price
                position_value = p.quantity * price

                total_market_value += position_value

                maintenance_requirement += (
                    position_value *
                    p.instrument.maintenance_margin_rate
                )
            except:
                continue

        total_cash = (
            Client.objects.aggregate(total=Sum("cash_balance"))["total"]
            or Decimal("0.00")
        )

        # -----------------------------
        # Institutional House Margin Level
        # -----------------------------
        net_equity = (
            total_market_value
            - total_principal
            - total_interest
        )

        if maintenance_requirement == 0:
            house_margin_level = Decimal("999.99")
        else:
            house_margin_level = (
                net_equity / maintenance_requirement
            ) * Decimal("100")

        return {
            "total_principal": total_principal.quantize(Decimal("0.01")),
            "total_interest": total_interest.quantize(Decimal("0.01")),
            "total_market_value": total_market_value.quantize(Decimal("0.01")),
            "total_cash": total_cash.quantize(Decimal("0.01")),
            "maintenance_requirement": maintenance_requirement.quantize(Decimal("0.01")),
            "house_margin_level": house_margin_level.quantize(Decimal("0.01")),
        }
