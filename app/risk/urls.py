from rest_framework.routers import DefaultRouter
from django.urls import path
from .views import (
    ClientRiskProfileViewSet,
    HouseRiskDashboardAPIView,
)

router = DefaultRouter()
router.register("risk-profiles", ClientRiskProfileViewSet)

urlpatterns = router.urls + [
    path("house-risk/", HouseRiskDashboardAPIView.as_view(), name="house-risk"),
]
