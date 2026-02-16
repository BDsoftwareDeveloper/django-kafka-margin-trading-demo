from django.core.management.base import BaseCommand
from risk.services.interest_service import InterestAccrualService


class Command(BaseCommand):
    help = "Accrue daily margin interest"

    def handle(self, *args, **kwargs):
        InterestAccrualService.accrue_daily_interest()
        self.stdout.write(self.style.SUCCESS("Daily interest accrued."))
