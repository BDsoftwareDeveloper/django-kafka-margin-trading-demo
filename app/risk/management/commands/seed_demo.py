from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from core.models import Client, Instrument, MarginLoan, Portfolio, AuditLog
from faker import Faker
import random

class Command(BaseCommand):
    help = 'Seed demo data for OMS Margin Trading System'

    def handle(self, *args, **options):
        fake = Faker()
        
        # Clear existing data
        Client.objects.all().delete()
        Instrument.objects.all().delete()
        
        # Create clients
        clients = []
        for _ in range(10):
            client = Client.objects.create(
                name=fake.name(),
                email=fake.email()
            )
            clients.append(client)
        
        # Create instruments
        instruments_data = [
            {'symbol': 'AAPL', 'name': 'Apple Inc.', 'exchange': 'NASDAQ', 'is_marginable': True, 'margin_rate': 0.3},
            {'symbol': 'GOOGL', 'name': 'Alphabet Inc.', 'exchange': 'NASDAQ', 'is_marginable': True, 'margin_rate': 0.35},
            {'symbol': 'MSFT', 'name': 'Microsoft Corp.', 'exchange': 'NASDAQ', 'is_marginable': True, 'margin_rate': 0.3},
            {'symbol': 'TSLA', 'name': 'Tesla Inc.', 'exchange': 'NASDAQ', 'is_marginable': True, 'margin_rate': 0.5},
            {'symbol': 'NVDA', 'name': 'NVIDIA Corp.', 'exchange': 'NASDAQ', 'is_marginable': True, 'margin_rate': 0.4},
        ]
        
        instruments = []
        for data in instruments_data:
            instrument, created = Instrument.objects.get_or_create(**data)
            instruments.append(instrument)
        
        # Create margin loans
        for client in clients:
            for _ in range(random.randint(1, 3)):
                MarginLoan.objects.create(
                    client=client,
                    loan_amount=round(random.uniform(1000, 50000), 2),
                    interest_rate=round(random.uniform(0.05, 0.12), 4)
                )
        
        # Create portfolio entries
        for client in clients:
            for instrument in random.sample(instruments, random.randint(1, 4)):
                Portfolio.objects.create(
                    client=client,
                    instrument=instrument,
                    quantity=random.randint(10, 1000),
                    avg_price=round(random.uniform(10, 500), 2)
                )
        
        self.stdout.write(
            self.style.SUCCESS('Successfully seeded demo data!')
        )