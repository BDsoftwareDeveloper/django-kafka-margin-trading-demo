from django.db import transaction
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from drf_spectacular.utils import extend_schema
from django.db.models import Count
from core.models import Client

from risk.models import ClientRiskProfile, ClientGroup, ExposureTemplate
from risk.serializers import (
    ClientRiskProfileSerializer,
    ClientGroupSerializer,
    HouseRiskSerializer,
    ExposureTemplateSerializer
)
from risk.services.risk_engine import RiskEngine
from risk.services.house_risk_service import HouseRiskService







# =========================================================
# CLIENT GROUP VIEWSET
# =========================================================

class ClientGroupViewSet(viewsets.ModelViewSet):
    """
    Manage Client Groups
    Used for exposure template assignment and client grouping
    """

    queryset = (
        ClientGroup.objects
        .prefetch_related("exposure_templates", "clients")
        .annotate(client_count=Count("clients"))
    )

    serializer_class = ClientGroupSerializer
    permission_classes = [IsAuthenticated]

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]

    filterset_fields = [
        "is_active",
    ]

    search_fields = [
        "name",
        "description",
    ]

    ordering_fields = [
        "name",
        "created_at",
        "client_count",
    ]

    ordering = ["name"]
    
   

    @action(detail=False, methods=["get"])
    def available_clients(self, request):
        """
        Fetch clients available for grouping.
        Supports filtering.
        """

        clients = Client.objects.all()

        group_null = request.query_params.get("group__isnull")

        if group_null == "true":
            clients = clients.filter(group__isnull=True)

        search = request.query_params.get("search")
        if search:
            clients = clients.filter(
                client_code__icontains=search
            )

        data = [
            {
                "id": c.id,
                "client_code": c.client_code,
                "name": c.name,
                "category": c.category,
            }
            for c in clients
        ]

        return Response(data)

# =========================================================
# CLIENT RISK PROFILE VIEWSET
# =========================================================

class ClientRiskProfileViewSet(viewsets.ModelViewSet):
    """
    Institutional Risk Profile API (Equity-Based)
    Read-only monitoring + admin control endpoints
    """

    permission_classes = [IsAuthenticated]
    queryset = ClientRiskProfile.objects.select_related("client")
    serializer_class = ClientRiskProfileSerializer
    http_method_names = ["get"]  # 🔒 read-only list/retrieve

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]

    filterset_fields = [
        "current_status",
        "allow_margin",
    ]

    search_fields = [
        "client__client_code",
        "client__name",
    ]

    ordering_fields = [
        "updated_at",
        "current_status",
    ]

    ordering = ["-updated_at"]

    # ---------------------------------------------------
    # LIVE EQUITY SNAPSHOT
    # ---------------------------------------------------

    @extend_schema(
        description="Get real-time institutional equity-based margin snapshot",
    )
    @action(detail=True, methods=["get"], url_path="snapshot")
    def snapshot(self, request, pk=None):

        risk = self.get_object()
        client = risk.client

        snapshot = RiskEngine.equity_snapshot(client.id)

        return Response({
            "client_id": client.id,
            "client_code": client.client_code,
            "client_name": client.name,

            "cash_balance": str(client.cash_balance),

            "market_value": str(snapshot["market_value"]),
            "loan": str(snapshot["loan"]),
            "net_equity": str(snapshot["net_equity"]),
            "maintenance_requirement": str(snapshot["maintenance_requirement"]),
            "margin_level_percent": str(snapshot["margin_level_percent"]),

            "margin_status": risk.current_status,
            "allow_margin": risk.allow_margin,

            "thresholds": {
                "warning_level": str(risk.warning_level),
                "margin_call_level": str(risk.margin_call_level),
                "force_sell_level": str(risk.force_sell_level),
            }
        })

    # ---------------------------------------------------
    # FORCE RE-EVALUATE STATUS
    # ---------------------------------------------------

    @extend_schema(
        description="Re-evaluate client margin status (equity-based engine)",
    )
    @action(detail=True, methods=["post"], permission_classes=[IsAdminUser])
    def recheck(self, request, pk=None):

        risk = self.get_object()

        RiskEngine.enforce_margin_policy(risk.client_id)

        snapshot = RiskEngine.equity_snapshot(risk.client_id)

        return Response({
            "client_id": risk.client_id,
            "margin_level_percent": str(snapshot["margin_level_percent"]),
            "new_status": risk.current_status,
            "allow_margin": risk.allow_margin,
        })

    # ---------------------------------------------------
    # ADMIN OVERRIDE
    # ---------------------------------------------------

    @extend_schema(
        description="Manual margin override (Admin only)",
    )
    @action(detail=True, methods=["post"], permission_classes=[IsAdminUser])
    def toggle_margin(self, request, pk=None):

        risk = self.get_object()
        allow = request.data.get("allow_margin")

        if allow is None:
            return Response(
                {"error": "allow_margin is required (true/false)"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if isinstance(allow, bool):
            value = allow
        elif isinstance(allow, str):
            value = allow.lower() in ("true", "1", "yes")
        else:
            value = False

        risk.allow_margin = value
        risk.save(update_fields=["allow_margin"])

        return Response({
            "client_id": risk.client_id,
            "allow_margin": risk.allow_margin,
        })


# =========================================================
# HOUSE RISK DASHBOARD API
# =========================================================

class HouseRiskDashboardAPIView(APIView):
    """
    Institutional House Risk Monitoring API
    Provides real-time snapshot of house-level margin exposure.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["House Risk"],
        responses=HouseRiskSerializer,
        description="Institutional house-level margin monitoring snapshot",
    )
    def get(self, request):

        data = HouseRiskService.snapshot()
        serializer = HouseRiskSerializer(data)

        return Response(serializer.data)
    
        
class ExposureTemplateViewSet(viewsets.ModelViewSet):
    """
    Enterprise Exposure Template Management API
    
    Supports:
    - Manual templates
    - PE-based templates
    - Sector templates
    - Hybrid templates
    - Global fallback
    - Priority ordering
    """
    

    serializer_class = ExposureTemplateSerializer
    permission_classes = [IsAuthenticated]

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]

    filterset_fields = [
        "is_active",
        "is_system",
        "template_type",
        "sector",
        "priority",
    ]

    search_fields = ["name", "description"]

    ordering_fields = [
        "priority",
        "name",
        "created_at",
        "max_exposure_percent",
    ]

    ordering = ["priority", "name"]

    # ---------------------------------------------------
    # Optimized queryset
    # ---------------------------------------------------
    def get_queryset(self):
        return (
            ExposureTemplate.objects
            .prefetch_related("instruments", "client_groups")
            .order_by("priority", "name")
        )

    # ---------------------------------------------------
    # Metadata (Frontend Dynamic Form Control)
    # ---------------------------------------------------
    @action(detail=False, methods=["get"], url_path="metadata")
    def metadata(self, request):

        return Response({
            "template_types": [
                {"value": key, "label": label}
                for key, label in ExposureTemplate.TEMPLATE_TYPE_CHOICES
            ],
            "field_rules": {
                "MANUAL": {
                    "show": ["instrument_symbols"],
                    "required": ["instrument_symbols"]
                },
                "PE": {
                    "show": ["min_pe", "max_pe"],
                    "required": ["min_pe"]
                },
                "SECTOR": {
                    "show": ["sector"],
                    "required": ["sector"]
                },
                "HYBRID": {
                    "show": ["sector", "min_pe", "max_pe"],
                    "required": ["sector", "min_pe"]
                },
                "GLOBAL": {
                    "show": [],
                    "required": []
                }
            }
        })

    # ---------------------------------------------------
    # Restrict create/update/delete to admin
    # ---------------------------------------------------
    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy",
                           "assign_group", "remove_group"]:
            return [IsAdminUser()]
        return [IsAuthenticated()]

    # ---------------------------------------------------
    # Protect system template from modification
    # ---------------------------------------------------
    def perform_update(self, serializer):
        instance = self.get_object()

        if instance.is_system:
            raise ValidationError("System template cannot be modified.")

        serializer.save()

    # ---------------------------------------------------
    # Prevent deletion of system template
    # ---------------------------------------------------
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()

        if instance.is_system:
            return Response(
                {"error": "System template cannot be deleted."},
                status=status.HTTP_400_BAD_REQUEST
            )

        return super().destroy(request, *args, **kwargs)

    # ---------------------------------------------------
    # Bulk Assign Groups
    # ---------------------------------------------------
    @action(detail=True, methods=["post"])
    @transaction.atomic
    def assign_group(self, request, pk=None):

        template = self.get_object()
        group_ids = request.data.get("group_ids")

        if not group_ids or not isinstance(group_ids, list):
            return Response(
                {"error": "group_ids list is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        groups = ClientGroup.objects.filter(id__in=group_ids)

        if groups.count() != len(group_ids):
            return Response(
                {"error": "One or more group_ids are invalid."},
                status=status.HTTP_400_BAD_REQUEST
            )

        template.client_groups.add(*groups)

        return Response({
            "message": "Groups assigned successfully.",
            "assigned_count": groups.count()
        })

    # ---------------------------------------------------
    # Bulk Remove Groups
    # ---------------------------------------------------
    @action(detail=True, methods=["post"])
    @transaction.atomic
    def remove_group(self, request, pk=None):

        template = self.get_object()
        group_ids = request.data.get("group_ids")

        if not group_ids or not isinstance(group_ids, list):
            return Response(
                {"error": "group_ids list is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        groups = ClientGroup.objects.filter(id__in=group_ids)
        template.client_groups.remove(*groups)

        return Response({
            "message": "Groups removed successfully.",
            "removed_count": groups.count()
        })

    # ---------------------------------------------------
    # Preview resolved instruments (Paginated)
    # ---------------------------------------------------
    @action(detail=True, methods=["get"])
    def preview_instruments(self, request, pk=None):

        template = self.get_object()
        serializer = self.get_serializer(template)

        instruments = serializer._resolve_instruments(template)

        page = self.paginate_queryset(instruments)
        if page is not None:
            return self.get_paginated_response([
                {
                    "symbol": i.symbol,
                    "sector": i.sector,
                    "pe_ratio": i.pe_ratio,
                }
                for i in page
            ])

        return Response({
            "template": template.name,
            "instrument_count": instruments.count(),
            "instruments": [
                {
                    "symbol": i.symbol,
                    "sector": i.sector,
                    "pe_ratio": i.pe_ratio,
                }
                for i in instruments
            ],
        })