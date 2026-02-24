from rest_framework.routers import DefaultRouter
from django.urls import path
from .views import (
    ClientRiskProfileViewSet,
    ClientGroupViewSet,
    ExposureTemplateViewSet,
    HouseRiskDashboardAPIView,
)

router = DefaultRouter()

# Risk Profiles
router.register("risk-profiles", ClientRiskProfileViewSet, basename="risk-profile")

# Client Groups
router.register("client-groups", ClientGroupViewSet, basename="client-group")

# Exposure Templates
router.register("exposure-templates", ExposureTemplateViewSet, basename="exposure-template")

urlpatterns = router.urls + [
    path("house-risk/", HouseRiskDashboardAPIView.as_view(), name="house-risk"),
]