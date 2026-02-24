import django_filters
from core.models import MarginLoan, AuditLog, Client, Instrument, Portfolio

class ClientFilter(django_filters.FilterSet):
    start_date = django_filters.DateFilter(
        field_name="created_at",
        lookup_expr="date__gte"
    )
    end_date = django_filters.DateFilter(
        field_name="created_at",
        lookup_expr="date__lte"
    )

    class Meta:
        model = Client
        fields = ["client_code"]


class InstrumentFilter(django_filters.FilterSet):
    start_date = django_filters.DateFilter(
        field_name="created_at",
        lookup_expr="date__gte"
    )
    end_date = django_filters.DateFilter(
        field_name="created_at",
        lookup_expr="date__lte"
    )

    class Meta:
        model = Instrument
        fields = ["is_marginable", "symbol"]


class MarginLoanFilter(django_filters.FilterSet):

    start_date = django_filters.DateFilter(
        field_name="opened_at",
        lookup_expr="date__gte"
    )

    end_date = django_filters.DateFilter(
        field_name="opened_at",
        lookup_expr="date__lte"
    )

    status = django_filters.CharFilter(
        field_name="status",
        lookup_expr="iexact"
    )

    min_amount = django_filters.NumberFilter(
        field_name="principal_amount",
        lookup_expr="gte"
    )

    max_amount = django_filters.NumberFilter(
        field_name="principal_amount",
        lookup_expr="lte"
    )

    class Meta:
        model = MarginLoan
        fields = ["client", "status", "principal_amount"]



class AuditLogFilter(django_filters.FilterSet):

    start_date = django_filters.DateFilter(
        field_name="created_at",
        lookup_expr="date__gte"
    )

    end_date = django_filters.DateFilter(
        field_name="created_at",
        lookup_expr="date__lte"
    )

    class Meta:
        model = AuditLog
        fields = ["event_type", "client"]   # ✅ correct field name




class PortfolioFilter(django_filters.FilterSet):

    start_date = django_filters.DateFilter(
        field_name="updated_at",   # ✅ NOT created_at
        lookup_expr="date__gte"
    )

    end_date = django_filters.DateFilter(
        field_name="updated_at",
        lookup_expr="date__lte"
    )

    class Meta:
        model = Portfolio
        fields = ["client", "instrument"]


