import os
from pathlib import Path
from datetime import timedelta

from config.env import *


BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = ENV_SECRET_KEY


AUTH_USER_MODEL = "accounts.UserModel"

AUTHENTICATION_BACKENDS = [
    "apps.authentication.backends.AuthIranPhoneBackend",
]


# ---------------------------------------------------------------
# Installed Apps Configuration
# ---------------------------------------------------------------
INSTALLED_APPS = [
    # Default Django apps
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # 3rd party apps
    "corsheaders",
    "django_filters",
    "rest_framework",
    "drf_spectacular",
    "django_cleanup.apps.CleanupSelectedConfig",
    # Custom apps
    "apps.accounts",
    "apps.authentication",
    "apps.llm_chat",
]

# ---------------------------------------------------------------
# Middleware Configuration
# ---------------------------------------------------------------
MIDDLEWARE = [
    "debug_toolbar.middleware.DebugToolbarMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# ---------------------------------------------------------------
# URL Configuration
# ---------------------------------------------------------------
ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [os.path.join(BASE_DIR, "templates")],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# ---------------------------------------------------------------
# Password Validation
# ---------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ---------------------------------------------------------------
# Internationalization
# ---------------------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"

USE_TZ = True
USE_I18N = False


# ---------------------------------------------------------------
# Static Files
# ---------------------------------------------------------------
STATIC_URL = "/static/"


# ---------------------------------------------------------------
# Django REST Framework Configuration
# ---------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": [
        # "rest_framework.permissions.IsAuthenticated",
        "rest_framework.permissions.AllowAny",
    ],
    "DEFAULT_PAGINATION_CLASS": "common.pagination.DefaultPagination",
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.BasicAuthentication",
    ],
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.UserRateThrottle",
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.ScopedRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "10/minute",
        "user": "20/minute",
    },
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "WonderLand API",
    "DESCRIPTION": "API documentation",
    "VERSION": "1.0.0",
    # "SERVE_INCLUDE_SCHEMA": False,
}

# ---------------------------------------------------------------
# Email Configuration
# ---------------------------------------------------------------
EMAIL_BACKEND = ENV_EMAIL_BACKEND
EMAIL_HOST = ENV_EMAIL_HOST
EMAIL_PORT = ENV_EMAIL_PORT
EMAIL_USE_TLS = ENV_EMAIL_USE_TLS
EMAIL_HOST_USER = ENV_EMAIL_HOST_USER
EMAIL_HOST_PASSWORD = ENV_EMAIL_HOST_PASSWORD
DEFAULT_FROM_EMAIL = ENV_DEFAULT_FROM_EMAIL

# ---------------------------------------------------------------
# Celery Configuration
# ---------------------------------------------------------------
CELERY_BROKER_URL = "redis://localhost:6379/0"
CELERY_RESULT_BACKEND = "redis://localhost:6379/0"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "UTC"

# ---------------------------------------------------------------
# Simple JWT Configuration
# ---------------------------------------------------------------
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=ENV_MINUTES),
    "REFRESH_TOKEN_LIFETIME": timedelta(hours=ENV_HOURS),
    "AUTH_HEADER_TYPES": ("Bearer",),
    "UPDATE_LAST_LOGIN": True,
}
