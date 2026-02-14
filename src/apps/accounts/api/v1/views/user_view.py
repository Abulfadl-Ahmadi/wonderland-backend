import logging
from rest_framework import status, serializers
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.generics import RetrieveUpdateAPIView
from drf_spectacular.utils import (
    extend_schema,
    OpenApiExample,
    OpenApiParameter,
    OpenApiResponse,
    inline_serializer,
)

from apps.accounts.api.v1.serializers import UserSerializer

logger = logging.getLogger("app.v1.user_view")


UserDetailResponseSerializer = inline_serializer(
    name="UserDetailResponse",
    fields={
        "success": serializers.BooleanField(),
        "result": inline_serializer(
            name="UserDetailResult",
            fields={
                "user": UserSerializer(),
            },
        ),
        "message": serializers.CharField(),
    },
)

UserUpdateResponseSerializer = inline_serializer(
    name="UserUpdateResponse",
    fields={
        "success": serializers.BooleanField(),
        "result": UserSerializer(),
        "message": serializers.CharField(),
    },
)

ErrorResponseSerializer = inline_serializer(
    name="UserErrorResponse",
    fields={
        "success": serializers.BooleanField(),
        "message": serializers.CharField(),
        "errors": serializers.JSONField(required=False),
    },
)

AuthErrorResponseSerializer = inline_serializer(
    name="UserAuthErrorResponse",
    fields={
        "detail": serializers.CharField(),
    },
)


class UserView(RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "patch"]
    serializer_class = UserSerializer
    throttle_scope = "user"
    throttle_classes = [ScopedRateThrottle]

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="Authorization",
                description="Bearer access token. Example: Bearer <access>",
                required=True,
                location=OpenApiParameter.HEADER,
                type=str,
            )
        ],
        responses={
            200: OpenApiResponse(
                response=UserDetailResponseSerializer,
                description="User profile data returned.",
                examples=[
                    OpenApiExample(
                        "Success",
                        value={
                            "success": True,
                            "result": {
                                "user": {
                                    "id": "b3f0a8a3-4aa9-4b5e-9e23-6e2a1b7a5e21",
                                    "phone_number": "09123456789",
                                    "role": "user",
                                    "updatedAt": "2026-02-13T10:30:00Z",
                                    "createdAt": "2026-02-01T09:00:00Z",
                                    "profile": {
                                        "firstName": "Ali",
                                        "lastName": "Rezaei",
                                        "nationalCode": "1234567890",
                                    },
                                    "settings": {
                                        "theme": "dark",
                                        "language": "fa",
                                    },
                                }
                            },
                            "message": "User data retrieved successfully.",
                        },
                    )
                ],
            ),
            401: OpenApiResponse(
                response=AuthErrorResponseSerializer,
                description="Unauthorized.",
                examples=[
                    OpenApiExample(
                        "Unauthorized",
                        value={
                            "detail": "Authentication credentials were not provided."
                        },
                    )
                ],
            ),
            500: OpenApiResponse(
                response=ErrorResponseSerializer,
                description="Unexpected error.",
                examples=[
                    OpenApiExample(
                        "Unexpected error",
                        value={
                            "success": False,
                            "message": "Unexpected error.",
                            "errors": {"detail": "Unexpected error."},
                        },
                    )
                ],
            ),
        },
        description="Get current user profile. Requires Bearer auth.",
    )
    def get(self, request: Request, *args, **kwargs):
        user = request.user
        serializer = self.serializer_class(user, context={"request": request})

        logger.info(f"User {user.phone_number} requested their data via UserView")
        return Response(
            {
                "success": True,
                "result": {"user": serializer.data},
                "message": "User data retrieved successfully.",
            },
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="Authorization",
                description="Bearer access token. Example: Bearer <access>",
                required=True,
                location=OpenApiParameter.HEADER,
                type=str,
            )
        ],
        request=UserSerializer,
        responses={
            200: OpenApiResponse(
                response=UserUpdateResponseSerializer,
                description="User data updated.",
                examples=[
                    OpenApiExample(
                        "Success",
                        value={
                            "success": True,
                            "result": {
                                "id": "b3f0a8a3-4aa9-4b5e-9e23-6e2a1b7a5e21",
                                "phone_number": "09123456789",
                                "role": "user",
                                "updatedAt": "2026-02-13T10:35:00Z",
                                "createdAt": "2026-02-01T09:00:00Z",
                                "profile": {
                                    "firstName": "Ali",
                                    "lastName": "Rezaei",
                                    "nationalCode": "1234567890",
                                },
                                "settings": {
                                    "theme": "light",
                                    "language": "fa",
                                },
                            },
                            "message": "User data updated successfully.",
                        },
                    ),
                    OpenApiExample(
                        "Request example",
                        value={
                            "profile": {
                                "firstName": "Ali",
                                "lastName": "Rezaei",
                                "nationalCode": "1234567890",
                            },
                            "settings": {
                                "theme": "light",
                                "language": "fa",
                            },
                            "password": "NewPass1!",
                            "confirmPassword": "NewPass1!",
                        },
                        request_only=True,
                    ),
                ],
            ),
            400: OpenApiResponse(
                response=ErrorResponseSerializer,
                description="Validation error.",
                examples=[
                    OpenApiExample(
                        "Validation error",
                        value={
                            "success": False,
                            "message": "Validation error.",
                            "errors": {
                                "confirmPassword": [
                                    {
                                        "message": "Passwords do not match.",
                                        "code": "password_mismatch",
                                    }
                                ]
                            },
                        },
                    )
                ],
            ),
            401: OpenApiResponse(
                response=AuthErrorResponseSerializer,
                description="Unauthorized.",
                examples=[
                    OpenApiExample(
                        "Unauthorized",
                        value={
                            "detail": "Authentication credentials were not provided."
                        },
                    )
                ],
            ),
            500: OpenApiResponse(
                response=ErrorResponseSerializer,
                description="Unexpected error.",
                examples=[
                    OpenApiExample(
                        "Unexpected error",
                        value={
                            "success": False,
                            "message": "Unexpected error.",
                            "errors": {"detail": "Unexpected error."},
                        },
                    )
                ],
            ),
        },
        description="Update current user profile. Requires Bearer auth.",
    )
    def patch(self, request: Request, *args, **kwargs):
        user = request.user
        serializer = self.get_serializer(user, data=request.data, partial=True)

        try:
            serializer.is_valid(raise_exception=True)
            serializer.save()

            logger.info(f"User {user.phone_number} updated their data via UserView")
            return Response(
                {
                    "success": True,
                    "result": serializer.data,
                    "message": "User data updated successfully.",
                },
                status=status.HTTP_200_OK,
            )

        except ValidationError as ve:
            logger.warning(
                f"User {user.phone_number} submitted invalid data: {serializer.errors}"
            )
            return Response(
                {
                    "success": False,
                    "message": "Validation error.",
                    "errors": ve.get_full_details(),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        except Exception as e:
            logger.exception(
                f"Unexpected exception in UserView for user {user.phone_number}: {e}"
            )
            return Response(
                {
                    "success": False,
                    "message": "Unexpected error.",
                    "errors": {"detail": str(e)},
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )