# core/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ClientViewSet, InstrumentViewSet, PortfolioViewSet, MarginLoanViewSet, AuditLogViewSet

router = DefaultRouter()
router.register(r'client', ClientViewSet)
router.register(r'instrument', InstrumentViewSet)
router.register(r'portfolio', PortfolioViewSet)
router.register(r'margin-loan', MarginLoanViewSet)
router.register(r"audit-logs", AuditLogViewSet)

urlpatterns = [
    path('', include(router.urls)),
]