
# from django.contrib import admin
# from django.urls import path, include

# from drf_spectacular.views import (
#     SpectacularAPIView,
#     SpectacularSwaggerView,
#     SpectacularRedocView,
# )

# urlpatterns = [
#     path("admin/", admin.site.urls),

#     # Core OMS APIs
#     path("api/core/", include("core.urls")),

#     # 🔐 Risk Engine APIs
#     path("api/risk/", include("risk.urls")),   # ✅ ADD THIS

#     # OpenAPI schema
#     path("api/schema/", SpectacularAPIView.as_view(), name="schema"),

#     # Swagger UI
#     path(
#         "api/schema/swagger-ui/",
#         SpectacularSwaggerView.as_view(url_name="schema"),
#         name="swagger-ui",
#     ),

#     # ReDoc
#     path(
#         "api/schema/redoc/",
#         SpectacularRedocView.as_view(url_name="schema"),
#         name="redoc",
#     ),
# ]

from django.contrib import admin
from django.urls import path, include

from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)

# ✅ ADD THIS
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

urlpatterns = [
    path("admin/", admin.site.urls),

    # 🔐 JWT Authentication
    path("api/auth/login/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/auth/refresh/", TokenRefreshView.as_view(), name="token_refresh"),

    # Core OMS APIs
    path("api/core/", include("core.urls")),

    # Risk Engine APIs
    path("api/risk/", include("risk.urls")),

    # OpenAPI schema
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),

    # Swagger UI
    path(
        "api/schema/swagger-ui/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),

    # ReDoc
    path(
        "api/schema/redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),
]
