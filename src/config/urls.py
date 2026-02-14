from django.contrib import admin
from django.conf import settings
from rest_framework import routers
from django.urls import path, include
from django.conf.urls.static import static
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)

from .env import ENV_ADMIN_URL, ENV_BASE_URL


router = routers.DefaultRouter()

base_url: str = ENV_BASE_URL
admin_url: str = ENV_ADMIN_URL

urlpatterns = [
    path(base_url, include(router.urls)),
    # Admin URL without base_url
    path(base_url + admin_url, admin.site.urls),
    # OpenAPI schema and docs
    path(base_url + "schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        base_url + "docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path(
        base_url + "redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),
    # API v1 routes
    path(base_url + "v1/accounts/", include("apps.accounts.api.v1.urls")),
    path(base_url + "v1/authentication/", include("apps.authentication.api.v1.urls")),
    path(base_url + "v1/chat/", include("apps.llm_chat.api.v1.urls")),
]


if settings.DEBUG:
    urlpatterns += (path("__debug__/", include("debug_toolbar.urls")),)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


admin.site.index_title = "WonderLand Admin"
admin.site.site_header = "WonderLand Admin"
admin.site.site_title = "WonderLand"
