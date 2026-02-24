from decimal import Decimal
from django.utils import timezone
from risk.models import TemplateInstrument


class ExposureEngine:

    @staticmethod
    def get_template_for_instrument(instrument):

        now = timezone.now()

        links = (
            TemplateInstrument.objects
            .filter(
                instrument=instrument,
                template__is_active=True
            )
            .select_related("template")
            .order_by("priority")
        )

        for link in links:
            if link.is_active():
                return link.template

        return None

    @staticmethod
    def get_initial_margin_rate(instrument):

        template = ExposureEngine.get_template_for_instrument(instrument)

        if template:
            return template.initial_margin_rate

        # fallback to instrument default
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