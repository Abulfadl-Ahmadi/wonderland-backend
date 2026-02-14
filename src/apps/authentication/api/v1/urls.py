from django.urls import path

from .views import (
    LoginAPIView,
    RegisterAPIView,
    RefreshAPIView,
)


urlpatterns = [
    # Login
    path("login/", LoginAPIView.as_view(), name="login"),
    path("register/", RegisterAPIView.as_view(), name="register"),
    # Refresh
    path("refresh/", RefreshAPIView.as_view(), name="refresh"),
]