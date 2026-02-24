
# """
# Django settings for oms_margin_demo project.
# OMS Margin Loan System - Clean Dev Configuration
# """

# import os
# from pathlib import Path

# BASE_DIR = Path(__file__).resolve().parent.parent

# # =========================================================
# # SECURITY
# # =========================================================

# SECRET_KEY = os.environ.get(
#     "DJANGO_SECRET_KEY",
#     "django-insecure-change-this"
# )

# DEBUG = os.environ.get("DJANGO_DEBUG", "True") == "True"

# ALLOWED_HOSTS = [
#     "localhost",
#     "127.0.0.1",
#     "192.168.1.214",
# ]

# # =========================================================
# # BACKOFFICE API
# # =========================================================

# BACKOFFICE_BASE_URL = os.environ.get("BACKOFFICE_BASE_URL")
# BACKOFFICE_USERNAME = os.environ.get("BACKOFFICE_USERNAME")
# BACKOFFICE_PASSWORD = os.environ.get("BACKOFFICE_PASSWORD")

# # =========================================================
# # APPLICATIONS
# # =========================================================

# INSTALLED_APPS = [
#     # Django Core
#     "django.contrib.admin",
#     "django.contrib.auth",
#     "django.contrib.contenttypes",
#     "django.contrib.sessions",
#     "django.contrib.messages",
#     "django.contrib.staticfiles",

#     # Third-party
#     "corsheaders",
#     "rest_framework",
#     "drf_spectacular",
#     "drf_spectacular_sidecar",
#     "django_filters",

#     # Local apps
#     "accounts",
#     "core",
#     "backoffice",
#     "risk.apps.RiskConfig",
# ]

# # =========================================================
# # MIDDLEWARE
# # =========================================================

# MIDDLEWARE = [
#     "django.middleware.security.SecurityMiddleware",
#     "corsheaders.middleware.CorsMiddleware",  # MUST stay high
#     "django.contrib.sessions.middleware.SessionMiddleware",
#     "django.middleware.common.CommonMiddleware",
#     "django.middleware.csrf.CsrfViewMiddleware",
#     "django.contrib.auth.middleware.AuthenticationMiddleware",
#     "django.contrib.messages.middleware.MessageMiddleware",
#     "django.middleware.clickjacking.XFrameOptionsMiddleware",
# ]

# ROOT_URLCONF = "oms_margin_demo.urls"
# WSGI_APPLICATION = "oms_margin_demo.wsgi.application"

# # =========================================================
# # TEMPLATES (Required for Admin)
# # =========================================================

# TEMPLATES = [
#     {
#         "BACKEND": "django.template.backends.django.DjangoTemplates",
#         "DIRS": [BASE_DIR / "templates"],
#         "APP_DIRS": True,
#         "OPTIONS": {
#             "context_processors": [
#                 "django.template.context_processors.debug",
#                 "django.template.context_processors.request",
#                 "django.contrib.auth.context_processors.auth",
#                 "django.contrib.messages.context_processors.messages",
#             ],
#         },
#     },
# ]

# # =========================================================
# # DATABASE (PostgreSQL - Docker Ready)
# # =========================================================

# DATABASES = {
#     "default": {
#         "ENGINE": "django.db.backends.postgresql",
#         "NAME": os.environ.get("POSTGRES_DB", "omsdb"),
#         "USER": os.environ.get("POSTGRES_USER", "omsuser"),
#         "PASSWORD": os.environ.get("POSTGRES_PASSWORD", "omspassword"),
#         "HOST": os.environ.get("POSTGRES_HOST", "db"),
#         "PORT": os.environ.get("POSTGRES_PORT", "5432"),
#     }
# }

# # =========================================================
# # KAFKA
# # =========================================================

# KAFKA_BOOTSTRAP_SERVERS = os.environ.get(
#     "KAFKA_BOOTSTRAP_SERVERS",
#     "kafka:9092"
# ).split(",")

# # =========================================================
# # DRF CONFIG (Session Authentication)
# # =========================================================

# REST_FRAMEWORK = {
#     "DEFAULT_AUTHENTICATION_CLASSES": (
#         "rest_framework_simplejwt.authentication.JWTAuthentication",
#     ),
#     "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
#     "DEFAULT_PAGINATION_CLASS": "core.pagination.StandardResultsSetPagination",
#     "PAGE_SIZE": 20,

#     "DEFAULT_FILTER_BACKENDS": (
#         "django_filters.rest_framework.DjangoFilterBackend",
#         "rest_framework.filters.SearchFilter",
#         "rest_framework.filters.OrderingFilter",
#     ),
# }




# # =========================================================
# # SWAGGER / OPENAPI
# # =========================================================

# SPECTACULAR_SETTINGS = {
#     "TITLE": "OMS Margin API",
#     "DESCRIPTION": "Order & Margin Management System",
#     "VERSION": "1.0.0",
# }

# # =========================================================
# # CORS CONFIG (React Support)
# # =========================================================

# CORS_ALLOWED_ORIGINS = [
#     "http://localhost:3000",
#     "http://127.0.0.1:3000",
# ]

# CORS_ALLOW_CREDENTIALS = True

# CORS_ALLOW_HEADERS = [
#     "authorization",
#     "content-type",
#     "x-csrftoken",
# ]

# # =========================================================
# # CSRF CONFIG
# # =========================================================

# CSRF_TRUSTED_ORIGINS = [
#     "http://localhost:3000",
#     "http://127.0.0.1:3000",
# ]

# SESSION_COOKIE_SAMESITE = "Lax"
# CSRF_COOKIE_SAMESITE = "Lax"

# # IMPORTANT FOR LOCAL HTTP DEV
# SESSION_COOKIE_SECURE = False
# CSRF_COOKIE_SECURE = False

# # =========================================================
# # PASSWORD VALIDATION
# # =========================================================

# AUTH_PASSWORD_VALIDATORS = [
#     {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
#     {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
#     {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
#     {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
# ]

# # =========================================================
# # INTERNATIONALIZATION
# # =========================================================

# LANGUAGE_CODE = "en-us"
# TIME_ZONE = "UTC"
# USE_I18N = True
# USE_TZ = True

# # =========================================================
# # STATIC FILES
# # =========================================================

# STATIC_URL = "/static/"
# STATIC_ROOT = BASE_DIR / "staticfiles"

# DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"



"""
Django settings for oms_margin_demo project.
OMS Margin Loan System - JWT Production Configuration
"""

import os
from pathlib import Path
from datetime import timedelta

BASE_DIR = Path(__file__).resolve().parent.parent

# =========================================================
# SECURITY
# =========================================================

SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY",
    "django-insecure-change-this"
)

DEBUG = os.environ.get("DJANGO_DEBUG", "True") == "True"

ALLOWED_HOSTS = [
    "localhost",
    "127.0.0.1",
    "192.168.1.214",
]

# =========================================================
# BACKOFFICE API
# =========================================================

BACKOFFICE_BASE_URL = os.environ.get("BACKOFFICE_BASE_URL")
BACKOFFICE_USERNAME = os.environ.get("BACKOFFICE_USERNAME")
BACKOFFICE_PASSWORD = os.environ.get("BACKOFFICE_PASSWORD")

# =========================================================
# APPLICATIONS
# =========================================================

INSTALLED_APPS = [
    # Django Core
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # Third-party
    "corsheaders",
    "rest_framework",
    "rest_framework_simplejwt",
    "drf_spectacular",
    "drf_spectacular_sidecar",
    "django_filters",

    # Local apps
    "accounts",
    "core",
    "backoffice",
    "risk.apps.RiskConfig",
]

# =========================================================
# MIDDLEWARE
# =========================================================

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "oms_margin_demo.urls"
WSGI_APPLICATION = "oms_margin_demo.wsgi.application"

# =========================================================
# TEMPLATES (Admin Required)
# =========================================================

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# =========================================================
# DATABASE (PostgreSQL - Docker Ready)
# =========================================================

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("POSTGRES_DB", "omsdb"),
        "USER": os.environ.get("POSTGRES_USER", "omsuser"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD", "omspassword"),
        "HOST": os.environ.get("POSTGRES_HOST", "db"),
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
    }
}

# =========================================================
# KAFKA
# =========================================================

KAFKA_BOOTSTRAP_SERVERS = os.environ.get(
    "KAFKA_BOOTSTRAP_SERVERS",
    "kafka:9092"
).split(",")

# =========================================================
# DJANGO REST FRAMEWORK
# =========================================================

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PAGINATION_CLASS": "core.pagination.StandardResultsSetPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ),
}

# =========================================================
# SIMPLE JWT CONFIG (30 DAYS ACCESS TOKEN)
# =========================================================

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(days=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=60),
    "ROTATE_REFRESH_TOKENS": False,
    "BLACKLIST_AFTER_ROTATION": False,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

# =========================================================
# SWAGGER / OPENAPI
# =========================================================

SPECTACULAR_SETTINGS = {
    "TITLE": "OMS Margin API",
    "DESCRIPTION": "Order & Margin Management System",
    "VERSION": "1.0.0",
}

# =========================================================
# CORS CONFIG (React Frontend)
# =========================================================

CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

CORS_ALLOW_HEADERS = [
    "authorization",
    "content-type",
]

# =========================================================
# PASSWORD VALIDATION
# =========================================================

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# =========================================================
# INTERNATIONALIZATION
# =========================================================

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# =========================================================
# STATIC FILES
# =========================================================

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# =========================================================
# PRODUCTION SECURITY (AUTO WHEN DEBUG=False)
# =========================================================

if not DEBUG:
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
