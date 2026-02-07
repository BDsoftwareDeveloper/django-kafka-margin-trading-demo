# core/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ClientViewSet,
    InstrumentViewSet,
    PortfolioViewSet,
    MarginLoanViewSet,
    AuditLogViewSet,
)

router = DefaultRouter()
router.register(r"clients", ClientViewSet, basename="client")
router.register(r"instruments", InstrumentViewSet, basename="instrument")
router.register(r"portfolios", PortfolioViewSet, basename="portfolio")
router.register(r"margin-loans", MarginLoanViewSet, basename="margin-loan")
router.register(r"audit-logs", AuditLogViewSet, basename="audit-log")

urlpatterns = [
    path("", include(router.urls)),
]
