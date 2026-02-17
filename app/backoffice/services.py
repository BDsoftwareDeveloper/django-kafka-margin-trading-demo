# backoffice/services.py

from decimal import Decimal
from django.db import transaction

from core.models import Client, Instrument, Portfolio
from .client import BackOfficeClient
from .signal_control import DisablePortfolioSignal
from .utils import is_market_open


# ----------------------------------------
# BOARD MAPPING (Update if BO changes)
# ----------------------------------------
BOARD_MAPPING = {
    1: "A",
    2: "B",
    3: "Z",
}


class BackOfficeSyncService:

    @transaction.atomic
    def run(self):

        if is_market_open():
            raise Exception("❌ BackOffice sync not allowed during market hours")

        client = BackOfficeClient()
        client.login()

        # -----------------------------
        # Fetch Data
        # -----------------------------
        investors_response = client.get_json("/GetInvestorList")
        instruments_response = client.get_json("/GetInstrumentList")

        investors = investors_response.get("data", [])
        instruments = instruments_response.get("data", [])

        positions_xml = client.get_xml("/ClientsPosition")
        limits_xml = client.get_xml("/ClientsLimit")

        positions = positions_xml.get("Positions", {}).get("InsertOne", [])
        limits = limits_xml.get("Clients", {}).get("Limits", [])

        # Ensure list format
        if not isinstance(positions, list):
            positions = [positions]

        if not isinstance(limits, list):
            limits = [limits]

        # -----------------------------
        # Sync Data
        # -----------------------------
        self.sync_clients(investors)
        self.sync_instruments(instruments)

        # Prevent Kafka + forced sell triggers
        with DisablePortfolioSignal():
            self.sync_positions(positions)

        self.sync_cash(limits)

    # ----------------------------------------
    # CLIENTS
    # ----------------------------------------
    def sync_clients(self, investors):
        for inv in investors:
            Client.objects.update_or_create(
                client_code=inv["investorCode"],
                defaults={
                    "name": inv["investorName"].strip(),
                    "email": inv.get("email") or f"{inv['investorCode']}@bo.local",
                    "is_active": inv.get("activityStatus") == "Active",
                },
            )

    # ----------------------------------------
    # INSTRUMENTS
    # ----------------------------------------
    def sync_instruments(self, instruments):

        for inst in instruments:

            board_type_id = inst.get("boardTypeID")
            board = BOARD_MAPPING.get(board_type_id, "A")  # Safe fallback

            Instrument.objects.update_or_create(
                symbol=inst["instrumentCode"],
                defaults={
                    "name": inst["instrumentName"],
                    "exchange": "DSE",
                    "board": board,
                    "is_active": inst.get("isActive", True),
                },
            )

    # ----------------------------------------
    # POSITIONS
    # ----------------------------------------
    def sync_positions(self, positions):
        for pos in positions:
            try:
                client = Client.objects.get(
                    client_code=pos["ClientCode"]
                )

                instrument = Instrument.objects.get(
                    symbol=pos["SecurityCode"]
                )

                quantity = Decimal(pos["Quantity"])
                total_cost = Decimal(pos["TotalCost"])

                avg_price = (
                    total_cost / quantity if quantity > 0 else Decimal("0")
                )

                Portfolio.objects.update_or_create(
                    client=client,
                    instrument=instrument,
                    defaults={
                        "quantity": quantity,
                        "avg_price": avg_price,
                    },
                )

            except Exception:
                continue

    # ----------------------------------------
    # CASH
    # ----------------------------------------
    def sync_cash(self, limits):
        for item in limits:
            try:
                client = Client.objects.get(
                    client_code=item["ClientCode"]
                )

                client.cash_balance = Decimal(item["Cash"])
                client.save(update_fields=["cash_balance"])

            except Client.DoesNotExist:
                continue
