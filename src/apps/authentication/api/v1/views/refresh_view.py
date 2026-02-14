from rest_framework import serializers
from rest_framework_simplejwt.views import TokenRefreshView
from drf_spectacular.utils import (
    extend_schema,
    OpenApiExample,
    OpenApiResponse,
    inline_serializer,
)


TokenRefreshRequestSerializer = inline_serializer(
    name="TokenRefreshRequest",
    fields={
        "refresh": serializers.CharField(),
    },
)

TokenRefreshResponseSerializer = inline_serializer(
    name="TokenRefreshResponse",
    fields={
        "access": serializers.CharField(),
        "refresh": serializers.CharField(required=False),
    },
)

AuthErrorResponseSerializer = inline_serializer(
    name="RefreshAuthErrorResponse",
    fields={
        "detail": serializers.CharField(),
    },
)


class RefreshAPIView(TokenRefreshView):
    @extend_schema(
        request=TokenRefreshRequestSerializer,
        responses={
            200: OpenApiResponse(
                response=TokenRefreshResponseSerializer,
                description="Access token refreshed successfully.",
                examples=[
                    OpenApiExample(
                        "Success",
                        value={
                            "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9",
                            "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9",
                        },
                    )
                ],
            ),
            401: OpenApiResponse(
                response=AuthErrorResponseSerializer,
                description="Invalid or expired refresh token.",
                examples=[
                    OpenApiExample(
                        "Invalid token",
                        value={"detail": "Token is invalid or expired"},
                    )
                ],
            ),
        },
        description="Exchange a refresh token for a new access token. No auth required.",
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)
