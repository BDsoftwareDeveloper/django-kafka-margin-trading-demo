
from kafka import KafkaProducer
import json, os

from decimal import Decimal
from django.utils import timezone
from core.models import Client, Instrument, Portfolio, MarginLoan, AuditLog

def approve_margin_loan(client: Client, loan_amount: Decimal):
    portfolio = Portfolio.objects.filter(client=client)
    portfolio_value = sum(
        p.current_value(market_price=100) for p in portfolio  # mock market price
    )

    marginable_value = sum(
        p.current_value(market_price=100) 
        for p in portfolio if p.instrument.is_marginable
    )

    if loan_amount <= marginable_value * Decimal("0.50"):  # 50% margin rule
        loan = MarginLoan.objects.create(client=client, loan_amount=loan_amount)
        AuditLog.log_event("LoanApproved", client, loan, {"amount": str(loan_amount)})
        return loan
    else:
        AuditLog.log_event("LoanRejected", client, None, {"requested": str(loan_amount)})
        return None







def check_and_force_sell(client: Client):
    broker = os.getenv("KAFKA_BROKER", "kafka:9092")
    producer = KafkaProducer(
        bootstrap_servers=[broker],
        value_serializer=lambda v: json.dumps(v).encode("utf-8")
    )

    loans = MarginLoan.objects.filter(client=client, loan_amount__gt=0)
    portfolio_value = sum(
        p.current_value(market_price=100) for p in Portfolio.objects.filter(client=client)
    )

    for loan in loans:
        if portfolio_value < loan.loan_amount:  # under-collateralized
            event = {"client": client.id, "loan_id": loan.id, "action": "FORCED_SELL"}
            producer.send("margin-events", event)
            producer.flush()
            AuditLog.log_event("ForcedSellTriggered", client, loan, event)

