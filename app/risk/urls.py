from rest_framework.routers import DefaultRouter
from .views import ClientRiskProfileViewSet

router = DefaultRouter()
router.register("risk-profiles", ClientRiskProfileViewSet)

urlpatterns = router.urls
