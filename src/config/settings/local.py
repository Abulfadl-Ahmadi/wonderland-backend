from .base import *


DEBUG = True
ENABLE_DEBUG_TOOLBAR = True

# ---------------------------------------------------------------
# Database Configuration
# ---------------------------------------------------------------
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "dev_db.sqlite3",
    }
}

INSTALLED_APPS.append("debug_toolbar")
MIDDLEWARE.insert(0, "debug_toolbar.middleware.DebugToolbarMiddleware")


# ---------------------------------------------------------------
# Allowed Hosts & Internal IPs
# ---------------------------------------------------------------
INTERNAL_IPS = ["localhost", "127.0.0.1"]
ALLOWED_HOSTS = ["localhost", "127.0.0.1"]

# ---------------------------------------------------------------
# CORS & CSRF Configuration
# ---------------------------------------------------------------
CORS_ALLOW_CREDENTIALS = True

CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
]

CSRF_TRUSTED_ORIGINS = [
    "http://localhost:3000",
]

CORS_ALLOW_METHODS = [
    "DELETE",
    "GET",
    "OPTIONS",
    "PATCH",
    "POST",
    "PUT",
]


# ---------------------------------------------------------------
# Static & Media Files
# ---------------------------------------------------------------
STATIC_URL = "static/"
STATIC_ROOT = os.path.join(BASE_DIR, "static")

MEDIA_URL = "media/"
MEDIA_ROOT = os.path.join(BASE_DIR, "media")


# ---------------------------------------------------------------
# Logging Configuration
# ---------------------------------------------------------------
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)


LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "fmt": "%(asctime)s %(levelname)s %(name)s %(message)s "
            "%(pathname)s %(lineno)d",
        },
        "console": {
            "format": "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "INFO",
            "formatter": "console",
        },
        "app_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": LOG_DIR / "app.log",
            "maxBytes": 10 * 1024 * 1024,  # 10 MB
            "backupCount": 5,
            "encoding": "utf-8",
            "level": "INFO",
            "formatter": "json",
        },
        "error_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": LOG_DIR / "errors.log",
            "maxBytes": 5 * 1024 * 1024,  # 5 MB
            "backupCount": 10,
            "encoding": "utf-8",
            "level": "ERROR",
            "formatter": "json",
        },
    },
    # Catch everything else
    "root": {
        "handlers": ["console", "app_file", "error_file"],
        "level": "INFO",
    },
    "loggers": {
        # Django core
        "django": {
            "handlers": ["console", "app_file", "error_file"],
            "level": "INFO",
            "propagate": False,
        },
        # HTTP 500 errors
        "django.request": {
            "handlers": ["console", "error_file"],
            "level": "ERROR",
            "propagate": False,
        },
        # runserver / gunicorn access logs
        "django.server": {
            "handlers": ["console", "app_file"],
            "level": "INFO",
            "propagate": False,
        },
        # Security warnings
        "django.security": {
            "handlers": ["console", "error_file"],
            "level": "WARNING",
            "propagate": False,
        },
        # Your project logs — USE THIS
        "project": {
            "handlers": ["console", "app_file", "error_file"],
            "level": "INFO",
            "propagate": False,
        },
    },
}
# Example usage:
# import logging
# logger = logging.getLogger("project")

# logger.info("Order created", extra={"order_id": order.id, "user_id": request.user.id})