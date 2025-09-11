from django.core.management.base import BaseCommand
from core.consumers import start_consumer

class Command(BaseCommand):
    help = "Start Kafka consumer for risk monitoring"

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Starting Kafka consumer..."))
        start_consumer()
