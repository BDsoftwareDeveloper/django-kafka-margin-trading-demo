from django.core.management.base import BaseCommand
from backoffice.services import BackOfficeSyncService


class Command(BaseCommand):

    help = "Run Safe BackOffice Sync"

    def handle(self, *args, **kwargs):

        BackOfficeSyncService().run()

        self.stdout.write(
            self.style.SUCCESS("✅ BackOffice sync completed safely")
        )
