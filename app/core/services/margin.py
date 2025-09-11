from core.models import Portfolio, MarginLoan

def check_margin_and_force_sell(event):
    client_id = event.get("client_id")
    portfolio_id = event.get("portfolio_id")

    try:
        portfolio = Portfolio.objects.get(id=portfolio_id, client_id=client_id)
        loans = MarginLoan.objects.filter(client_id=client_id)
        total_loan = sum(l.loan_amount for l in loans)

        portfolio_value = portfolio.quantity * portfolio.instrument.price

        if portfolio_value < total_loan:
            print(f"⚠️ Forced sell triggered for client={client_id}, portfolio={portfolio_id}")
            # Here you can publish back to Kafka or call Django signal
            return True
        else:
            print(f"✅ Portfolio {portfolio_id} is safe for client={client_id}")
            return False

    except Portfolio.DoesNotExist:
        print(f"❌ Portfolio {portfolio_id} not found for client {client_id}")
        return False
