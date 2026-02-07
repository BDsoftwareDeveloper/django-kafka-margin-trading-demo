# core/management/commands/seed_demo_data.py

from django.core.management.base import BaseCommand
from decimal import Decimal
from faker import Faker
import random

from core.models import Client, Instrument, MarginLoan, Portfolio


class Command(BaseCommand):
    help = "Seed demo data for OMS Margin Trading System (safe & idempotent)"

    def handle(self, *args, **options):
        fake = Faker()
        self.stdout.write("🌱 Seeding OMS demo data...")

        # ---- Clients ----
        clients = []
        for _ in range(10):
            email = fake.unique.email()
            client, _ = Client.objects.get_or_create(
                email=email,
                defaults={"name": fake.name()},
            )
            clients.append(client)

        # ---- Instruments (stable) ----
        instruments_data = [
            ("AAPL", "Apple Inc.", Decimal("0.30")),
            ("GOOGL", "Alphabet Inc.", Decimal("0.35")),
            ("MSFT", "Microsoft Corp.", Decimal("0.30")),
            ("TSLA", "Tesla Inc.", Decimal("0.50")),
            ("NVDA", "NVIDIA Corp.", Decimal("0.40")),
        ]

        instruments = []
        for symbol, name, margin_rate in instruments_data:
            instrument, _ = Instrument.objects.get_or_create(
                symbol=symbol,
                defaults={
                    "name": name,
                    "exchange": "NASDAQ",
                    "is_marginable": True,
                    "margin_rate": margin_rate,
                },
            )
            instruments.append(instrument)

        # ---- Portfolios ----
        for client in clients:
            for instrument in random.sample(instruments, random.randint(1, 4)):
                Portfolio.objects.get_or_create(
                    client=client,
                    instrument=instrument,
                    defaults={
                        "quantity": Decimal(random.randint(10, 1000)),
                        "avg_price": Decimal(
                            str(round(random.uniform(10, 500), 2))
                        ),
                    },
                )

        # ---- Margin Loans ----
        for client in clients:
            for _ in range(random.randint(1, 2)):
                MarginLoan.objects.create(
                    client=client,
                    loan_amount=Decimal(
                        str(round(random.uniform(1000, 50000), 2))
                    ),
                    interest_rate=Decimal(
                        str(round(random.uniform(0.05, 0.12), 4))
                    ),
                )

        self.stdout.write(
            self.style.SUCCESS("✅ OMS demo data seeded successfully")
        )
