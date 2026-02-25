from rest_framework import serializers
from risk.models import ClientRiskProfile
from risk.services.risk_engine import RiskEngine
from core.models import Instrument, Client
from risk.models import ExposureTemplate, ClientGroup

class ExposureTemplateSerializer(serializers.ModelSerializer):

    # -------- WRITE USING BUSINESS KEYS --------
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

    # -------- READ OUTPUT --------
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
            "max_exposure_percent",
            "is_active",
            "is_system",
            "created_at",

            # Write fields
            "instrument_symbols",
            "client_group_names",

            # Read fields
            "instruments",
            "client_groups",

            "instrument_count",
            "group_count",
        ]

    # ---------------------------------
    # READ SECTION
    # ---------------------------------

    def get_instruments(self, obj):
        return [
            {
                "symbol": i.symbol,
                "name": i.name,
                "board": i.board,
            }
            for i in obj.instruments.all()
        ]

    def get_client_groups(self, obj):
        return [
            {
                "name": g.name,
                "is_active": g.is_active,
            }
            for g in obj.client_groups.all()
        ]

    def get_instrument_count(self, obj):
        return obj.instruments.count()

    def get_group_count(self, obj):
        return obj.client_groups.count()

    # ---------------------------------
    # CREATE
    # ---------------------------------

    def create(self, validated_data):
        instrument_symbols = validated_data.pop("instrument_symbols", [])
        client_group_names = validated_data.pop("client_group_names", [])

        template = ExposureTemplate.objects.create(**validated_data)

        self._assign_relations(template, instrument_symbols, client_group_names)

        return template

    # ---------------------------------
    # UPDATE (Replace Mode)
    # ---------------------------------

    def update(self, instance, validated_data):
        instrument_symbols = validated_data.pop("instrument_symbols", None)
        client_group_names = validated_data.pop("client_group_names", None)

        instance = super().update(instance, validated_data)

        self._assign_relations(instance, instrument_symbols, client_group_names)

        return instance

    # ---------------------------------
    # RELATION ASSIGNMENT HELPER
    # ---------------------------------

    def _assign_relations(self, template, instrument_symbols, client_group_names):

        # Instruments
        if instrument_symbols is not None:
            instruments = list(
                Instrument.objects.filter(symbol__in=instrument_symbols)
            )

            if len(instruments) != len(instrument_symbols):
                raise serializers.ValidationError(
                    {"instrument_symbols": "One or more instrument symbols are invalid."}
                )

            template.instruments.set(instruments)

        # Client Groups
        if client_group_names is not None:
            groups = list(
                ClientGroup.objects.filter(name__in=client_group_names)
            )

            if len(groups) != len(client_group_names):
                raise serializers.ValidationError(
                    {"client_group_names": "One or more client group names are invalid."}
                )

            template.client_groups.set(groups)
    
    






# class ExposureTemplateSerializer(serializers.ModelSerializer):

#     # Write-only IDs
#     instrument_ids = serializers.PrimaryKeyRelatedField(
#         many=True,
#         queryset=Instrument.objects.all(),
#         source="instruments",
#         write_only=True,
#         required=False,
#     )

#     group_ids = serializers.PrimaryKeyRelatedField(
#         many=True,
#         queryset=ClientGroup.objects.all(),
#         source="client_groups",
#         write_only=True,
#         required=False,
#     )

#     # Read-only display
#     instruments = serializers.StringRelatedField(many=True, read_only=True)
#     client_groups = serializers.StringRelatedField(many=True, read_only=True)

#     instrument_count = serializers.SerializerMethodField()
#     group_count = serializers.SerializerMethodField()

#     class Meta:
#         model = ExposureTemplate
#         fields = [
#             "id",
#             "name",
#             "description",
#             "max_exposure_percent",
#             "is_active",
#             "is_system",
#             "created_at",

#             "instrument_ids",
#             "group_ids",

#             "instruments",
#             "client_groups",

#             "instrument_count",
#             "group_count",
#         ]

#     def get_instrument_count(self, obj):
#         return obj.instruments.count()

#     def get_group_count(self, obj):
#         return obj.client_groups.count()




# class ExposureTemplateSerializer(serializers.ModelSerializer):

#     # Write-only IDs
#     instrument_ids = serializers.PrimaryKeyRelatedField(
#         many=True,
#         queryset=Instrument.objects.all(),
#         write_only=True,
#         required=False,
#     )

#     group_ids = serializers.PrimaryKeyRelatedField(
#         many=True,
#         queryset=ClientGroup.objects.all(),
#         write_only=True,
#         required=False,
#     )

#     # Read-only structured output
#     instruments = serializers.SerializerMethodField()
#     client_groups = serializers.SerializerMethodField()

#     instrument_count = serializers.SerializerMethodField()
#     group_count = serializers.SerializerMethodField()

#     class Meta:
#         model = ExposureTemplate
#         fields = [
#             "id",
#             "name",
#             "description",
#             "max_exposure_percent",
#             "is_active",
#             "is_system",
#             "created_at",

#             "instrument_ids",
#             "group_ids",

#             "instruments",
#             "client_groups",

#             "instrument_count",
#             "group_count",
#         ]

#     # -------------------------
#     # READ METHODS
#     # -------------------------

#     def get_instruments(self, obj):
#         return [
#             {
#                 "id": i.id,
#                 "symbol": i.symbol,
#                 "board": i.board,
#             }
#             for i in obj.instruments.all()
#         ]

#     def get_client_groups(self, obj):
#         return [
#             {
#                 "id": g.id,
#                 "name": g.name,
#                 "is_active": g.is_active,
#             }
#             for g in obj.client_groups.all()
#         ]

#     def get_instrument_count(self, obj):
#         return obj.instruments.count()

#     def get_group_count(self, obj):
#         return obj.client_groups.count()

#     # -------------------------
#     # CREATE
#     # -------------------------

#     def create(self, validated_data):
#         instrument_ids = validated_data.pop("instrument_ids", [])
#         group_ids = validated_data.pop("group_ids", [])

#         template = ExposureTemplate.objects.create(**validated_data)

#         if instrument_ids:
#             template.instruments.set(instrument_ids)

#         if group_ids:
#             template.client_groups.set(group_ids)

#         return template

#     # -------------------------
#     # UPDATE (Replace Mode)
#     # -------------------------

#     def update(self, instance, validated_data):
#         instrument_ids = validated_data.pop("instrument_ids", None)
#         group_ids = validated_data.pop("group_ids", None)

#         instance = super().update(instance, validated_data)

#         if instrument_ids is not None:
#             instance.instruments.set(instrument_ids)

#         if group_ids is not None:
#             instance.client_groups.set(group_ids)

#         return instance

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