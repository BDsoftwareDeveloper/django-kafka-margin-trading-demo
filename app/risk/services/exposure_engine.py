from decimal import Decimal
from django.utils import timezone
from risk.models import ExposureTemplate


class ExposureEngine:

    # ---------------------------------------------------
    # INITIAL / MAINTENANCE MARGIN (unchanged)
    # ---------------------------------------------------

    @staticmethod
    def get_initial_margin_rate(instrument):

        template = ExposureEngine.get_template_for_instrument(instrument)

        if template:
            return template.initial_margin_rate

        return instrument.initial_margin_rate

    @staticmethod
    def get_maintenance_margin_rate(instrument):

        template = ExposureEngine.get_template_for_instrument(instrument)

        if template:
            return template.maintenance_margin_rate

        return instrument.maintenance_margin_rate

    @staticmethod
    def calculate_required_margin(instrument, trade_value):

        margin_rate = ExposureEngine.get_initial_margin_rate(instrument)
        return trade_value * margin_rate

    # ---------------------------------------------------
    # EXPOSURE LIMIT (PRIORITY SAFE)
    # ---------------------------------------------------

    @staticmethod
    def get_exposure_limit(client, instrument):

        if not client.group:
            return None

        templates = (
            ExposureTemplate.objects
            .filter(
                client_groups=client.group,
                is_active=True
            )
            .order_by("priority")  # ✅ CRITICAL FIX
        )

        for template in templates:

            # -------------------------
            # MANUAL (Highest Authority)
            # -------------------------
            if template.template_type == "MANUAL":
                if template.instruments.filter(id=instrument.id).exists():
                    return template.max_exposure_percent
                continue

            # -------------------------
            # SECTOR FILTER
            # -------------------------
            if template.sector:
                if instrument.sector != template.sector:
                    continue

            # -------------------------
            # PE FILTER
            # -------------------------
            if template.min_pe is not None:
                if (
                    instrument.pe_ratio is None
                    or instrument.pe_ratio < template.min_pe
                ):
                    continue

            if template.max_pe is not None:
                if (
                    instrument.pe_ratio is None
                    or instrument.pe_ratio > template.max_pe
                ):
                    continue

            # -------------------------
            # MATCH FOUND
            # -------------------------
            return template.max_exposure_percent

        # No rule matched
        return None