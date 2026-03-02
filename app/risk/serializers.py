from rest_framework import serializers
from risk.models import ClientRiskProfile
from risk.services.risk_engine import RiskEngine
from core.models import Instrument, Client
from risk.models import ExposureTemplate, ClientGroup
from django.db import transaction


from django.db.models import Q



class ExposureTemplateSerializer(serializers.ModelSerializer):

    # -----------------------------
    # WRITE INPUT
    # -----------------------------
    instrument_symbols = serializers.ListField(
        child=serializers.CharField(),
        write_only=True,
        required=False,
    )

    client_group_names = serializers.ListField(
        child=serializers.CharField(),
        write_only=True,
        required=False,
    )

    # -----------------------------
    # READ OUTPUT
    # -----------------------------
    instruments = serializers.SerializerMethodField()
    client_groups = serializers.SerializerMethodField()
    instrument_count = serializers.SerializerMethodField()
    group_count = serializers.SerializerMethodField()

    class Meta:
        model = ExposureTemplate
        fields = [
            "id",
            "name",
            "description",
            "template_type",
            "priority",  # backend controlled
            "sector",
            "max_exposure_percent",
            "min_pe",
            "max_pe",
            "is_active",
            "is_system",
            "created_at",
            "instrument_symbols",
            "client_group_names",
            "instruments",
            "client_groups",
            "instrument_count",
            "group_count",
        ]

        read_only_fields = ("created_at", "priority")

    # ---------------------------------------------------
    # VALIDATION
    # ---------------------------------------------------
    def validate(self, attrs):

        template_type = attrs.get("template_type")
        min_pe = attrs.get("min_pe")
        max_pe = attrs.get("max_pe")
        sector = attrs.get("sector")
        instrument_symbols = attrs.get("instrument_symbols")

        # Remove duplicates
        if instrument_symbols:
            attrs["instrument_symbols"] = list(set(instrument_symbols))

        # PE validation
        if min_pe is not None and max_pe is not None:
            if min_pe > max_pe:
                raise serializers.ValidationError(
                    {"min_pe": "min_pe cannot be greater than max_pe."}
                )

        # Template type rule consistency
        if template_type == "GLOBAL":
            if min_pe is not None or max_pe is not None or sector:
                raise serializers.ValidationError(
                    "GLOBAL template cannot have PE or sector rules."
                )

        if template_type == "MANUAL" and not instrument_symbols:
            raise serializers.ValidationError(
                "MANUAL template requires instrument_symbols."
            )

        return attrs

    # ---------------------------------------------------
    # CREATE
    # ---------------------------------------------------
    @transaction.atomic
    def create(self, validated_data):

        instrument_symbols = validated_data.pop("instrument_symbols", [])
        group_names = validated_data.pop("client_group_names", [])

        template = ExposureTemplate.objects.create(**validated_data)

        self._assign_relations(template, instrument_symbols, group_names)

        return template

    # ---------------------------------------------------
    # UPDATE
    # ---------------------------------------------------
    @transaction.atomic
    def update(self, instance, validated_data):

        instrument_symbols = validated_data.pop("instrument_symbols", None)
        group_names = validated_data.pop("client_group_names", None)

        instance = super().update(instance, validated_data)

        self._assign_relations(instance, instrument_symbols, group_names)

        return instance

    # ---------------------------------------------------
    # RELATION ASSIGNMENT
    # ---------------------------------------------------
    def _assign_relations(self, template, instrument_symbols, group_names):

        # Instruments
        if instrument_symbols is not None:

            instruments = Instrument.objects.filter(
                symbol__in=instrument_symbols
            )

            if instruments.count() != len(instrument_symbols):
                raise serializers.ValidationError(
                    {"instrument_symbols": "Invalid instrument symbol(s)."}
                )

            template.instruments.set(instruments)

        # Groups
        if group_names is not None:

            groups = ClientGroup.objects.filter(
                name__in=group_names
            )

            if groups.count() != len(group_names):
                raise serializers.ValidationError(
                    {"client_group_names": "Invalid client group name(s)."}
                )

            template.client_groups.set(groups)

    # ---------------------------------------------------
    # CENTRALIZED RESOLUTION LOGIC
    # ---------------------------------------------------
    def _resolve_instruments(self, obj):

        # MANUAL
        if obj.template_type == "MANUAL":
            return obj.instruments.all()

        qs = Instrument.objects.filter(is_active=True)

        # SECTOR / HYBRID
        if obj.template_type in ["SECTOR", "HYBRID"] and obj.sector:
            qs = qs.filter(sector=obj.sector)

        # PE / HYBRID
        if obj.template_type in ["PE", "HYBRID"]:
            if obj.min_pe is not None:
                qs = qs.filter(pe_ratio__gte=obj.min_pe)
            if obj.max_pe is not None:
                qs = qs.filter(pe_ratio__lte=obj.max_pe)

        return qs

    # ---------------------------------------------------
    # READ METHODS
    # ---------------------------------------------------
    def get_instruments(self, obj):

        instruments = self._resolve_instruments(obj)

        return [
            {
                "symbol": i.symbol,
                "sector": i.sector,
                "pe_ratio": i.pe_ratio,
            }
            for i in instruments[:50]  # protect API
        ]

    def get_instrument_count(self, obj):
        return self._resolve_instruments(obj).count()

    def get_client_groups(self, obj):
        return [
            {
                "name": g.name,
                "is_active": g.is_active,
                "client_count": g.clients.count(),
            }
            for g in obj.client_groups.all()
        ]

    def get_group_count(self, obj):
        return obj.client_groups.count()


class ClientRiskProfileSerializer(serializers.ModelSerializer):

    # ------------------------------
    # Client Info
    # ------------------------------
    client_name = serializers.CharField(
        source="client.name",
        read_only=True
    )

    cash_balance = serializers.DecimalField(
        source="client.cash_balance",
        max_digits=20,
        decimal_places=2,
        read_only=True,
    )

    # ------------------------------
    # Institutional Risk Metrics
    # ------------------------------
    market_value = serializers.SerializerMethodField()
    loan = serializers.SerializerMethodField()
    net_equity = serializers.SerializerMethodField()
    maintenance_requirement = serializers.SerializerMethodField()
    margin_level_percent = serializers.SerializerMethodField()
    margin_status = serializers.SerializerMethodField()

    class Meta:
        model = ClientRiskProfile
        fields = [
            "id",
            "client",
            "client_name",
            "cash_balance",

            # Margin Controls
            "allow_margin",
            "current_status",
            "warning_level",
            "margin_call_level",
            "force_sell_level",

            # Institutional Metrics
            "market_value",
            "loan",
            "net_equity",
            "maintenance_requirement",
            "margin_level_percent",
            "margin_status",
        ]

        read_only_fields = [
            "market_value",
            "loan",
            "net_equity",
            "maintenance_requirement",
            "margin_level_percent",
            "margin_status",
            "current_status",
        ]

    # --------------------------------------------
    # Snapshot (Single Calculation per Row)
    # --------------------------------------------
    def _snapshot(self, obj):
        return RiskEngine.equity_snapshot(obj.client_id)

    def get_market_value(self, obj):
        return str(self._snapshot(obj)["market_value"])

    def get_loan(self, obj):
        return str(self._snapshot(obj)["loan"])

    def get_net_equity(self, obj):
        return str(self._snapshot(obj)["net_equity"])

    def get_maintenance_requirement(self, obj):
        return str(self._snapshot(obj)["maintenance_requirement"])

    def get_margin_level_percent(self, obj):
        return str(self._snapshot(obj)["margin_level_percent"])

    def get_margin_status(self, obj):
        return RiskEngine.evaluate_margin_status(obj.client_id)




class HouseRiskSerializer(serializers.Serializer):

    total_principal = serializers.DecimalField(
        max_digits=20,
        decimal_places=2
    )

    total_interest = serializers.DecimalField(
        max_digits=20,
        decimal_places=2
    )

    total_market_value = serializers.DecimalField(
        max_digits=20,
        decimal_places=2
    )

    total_cash = serializers.DecimalField(
        max_digits=20,
        decimal_places=2
    )

    maintenance_requirement = serializers.DecimalField(
        max_digits=20,
        decimal_places=2
    )

    house_margin_level = serializers.DecimalField(
        max_digits=10,
        decimal_places=2
    )



class ClientGroupSerializer(serializers.ModelSerializer):

    client_codes = serializers.ListField(
        child=serializers.CharField(),
        write_only=True,
        required=False,
    )

    clients = serializers.SerializerMethodField()
    template_count = serializers.SerializerMethodField()

    class Meta:
        model = ClientGroup
        fields = [
            "id",
            "name",
            "description",
            "is_active",
            "created_at",
            "client_codes",
            "clients",
            "template_count",
        ]

    def get_clients(self, obj):
        return [
            {
                "client_code": c.client_code,
                "name": c.name,
            }
            for c in obj.clients.all()
        ]

    def get_template_count(self, obj):
        return obj.exposure_templates.count()

    def create(self, validated_data):
        client_codes = validated_data.pop("client_codes", [])
        group = ClientGroup.objects.create(**validated_data)

        if client_codes:
            clients = Client.objects.filter(client_code__in=client_codes)
            group.clients.update(group=None)
            clients.update(group=group)

        return group

    def update(self, instance, validated_data):
        client_codes = validated_data.pop("client_codes", None)

        instance = super().update(instance, validated_data)

        if client_codes is not None:
            instance.clients.update(group=None)
            clients = Client.objects.filter(client_code__in=client_codes)
            clients.update(group=instance)

        return instance