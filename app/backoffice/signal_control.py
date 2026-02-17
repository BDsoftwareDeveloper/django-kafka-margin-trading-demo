# backoffice/signal_control.py

from django.db.models.signals import post_save
from core.models import Portfolio
from core.signals import portfolio_updated


class DisablePortfolioSignal:

    def __enter__(self):
        post_save.disconnect(portfolio_updated, sender=Portfolio)

    def __exit__(self, exc_type, exc_val, exc_tb):
        post_save.connect(portfolio_updated, sender=Portfolio)
