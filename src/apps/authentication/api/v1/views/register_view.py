import logging
from rest_framework import status, serializers
from rest_framework.views import APIView
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.exceptions import ValidationError
from rest_framework.throttling import ScopedRateThrottle
from drf_spectacular.utils import (
    extend_schema,
    OpenApiExample,
    OpenApiResponse,
    inline_serializer,
)

from services import AuthService
from apps.authentication.api.v1.serializers import (
    RegisterSerializer,
)

logger = logging.getLogger("app.v1.register_view")


RegisterSuccessResponseSerializer = inline_serializer(
    name="RegisterSuccessResponse",
    fields={
        "success": serializers.BooleanField(),
        "result": serializers.CharField(),
        "message": serializers.CharField(),
    },
)

ErrorResponseSerializer = inline_serializer(
    name="RegisterErrorResponse",
    fields={
        "success": serializers.BooleanField(),
        "message": serializers.CharField(),
        "errors": serializers.JSONField(required=False),
    },
)


class RegisterAPIView(APIView):
    http_method_names = ["post"]
    permission_classes = [AllowAny]
    # Request rate limit
    throttle_scope = "anon"
    throttle_classes = [ScopedRateThrottle]

    @extend_schema(
        request=RegisterSerializer,
        responses={
            200: OpenApiResponse(
                response=RegisterSuccessResponseSerializer,
                description="Registration successful.",
                examples=[
                    OpenApiExample(
                        "Success",
                        value={
                            "success": True,
                            "result": "b3f0a8a3-4aa9-4b5e-9e23-6e2a1b7a5e21",
                            "message": "User registered successfully.",
                        },
                    )
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
            409: OpenApiResponse(
                response=ErrorResponseSerializer,
                description="Conflict. User already exists.",
                examples=[
                    OpenApiExample(
                        "Conflict",
                        value={
                            "success": False,
                            "message": "User already exists.",
                            "errors": {"detail": "Phone number already registered."},
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
        description=(
            "Register a new user with phone number and profile fields. No auth required."
        ),
    )
    def post(self, request: Request, *args, **kwargs):
        try:
            # Validate data
            serializer = RegisterSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            # Extract Data
            phone_number = serializer.validated_data["phoneNumber"]  # type: ignore
            password = serializer.validated_data["password"]  # type: ignore
            confirm_password = serializer.validated_data["confirmPassword"]  # type: ignore
            first_name = serializer.validated_data["firstName"]  # type: ignore
            last_name = serializer.validated_data["lastName"]  # type: ignore
            national_code = serializer.validated_data["nationalCode"]  # type: ignore
            # Register user via auth service
            user = AuthService.register(
                first_name=first_name,
                last_name=last_name,
                national_code=national_code,
                phone_number=phone_number,
                password=password,
                confirm_password=confirm_password,
            )
            # Log and return response
            logger.info(f"User {user} registered successfully via register api")
            return Response(
                data={
                    "success": True,
                    "result": user.id,
                    "message": "User registered successfully.",
                },
                status=status.HTTP_200_OK,
            )
        # Handle validation errors
        except ValidationError as ve:
            logger.warning(f"Invalid data in RegisterAPIView: {serializer.errors}") # type: ignore
            return Response(
                {
                    "success": False,
                    "message": "Validation error.",
                    "errors": ve.get_full_details(),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        # Handle exceptions
        except Exception as e:
            logger.error(f"Exception in RegisterAPIView: {e}")
            return Response(
                {
                    "success": False,
                    "message": "Unexpected error.",
                    "errors": {"detail": str(e)},
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )