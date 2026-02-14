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
    LoginSerializer,
)

logger = logging.getLogger("app.v1.login_view")


LoginSuccessResponseSerializer = inline_serializer(
    name="LoginSuccessResponse",
    fields={
        "success": serializers.BooleanField(),
        "result": inline_serializer(
            name="LoginTokenPair",
            fields={
                "access": serializers.CharField(),
                "refresh": serializers.CharField(),
            },
        ),
        "message": serializers.CharField(),
    },
)

ErrorResponseSerializer = inline_serializer(
    name="LoginErrorResponse",
    fields={
        "success": serializers.BooleanField(),
        "message": serializers.CharField(),
        "errors": serializers.JSONField(required=False),
    },
)


class LoginAPIView(APIView):
    http_method_names = ["post"]
    permission_classes = [AllowAny]
    # Request rate limit
    throttle_scope = "anon"
    throttle_classes = [ScopedRateThrottle]

    @extend_schema(
        request=LoginSerializer,
        responses={
            200: OpenApiResponse(
                response=LoginSuccessResponseSerializer,
                description="Login successful.",
                examples=[
                    OpenApiExample(
                        "Success",
                        value={
                            "success": True,
                            "result": {
                                "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9",
                                "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9",
                            },
                            "message": "User logged in successfully.",
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
                                "phoneNumber": [
                                    {
                                        "message": "Phone number is required",
                                        "code": "required",
                                    }
                                ]
                            },
                        },
                    )
                ],
            ),
            401: OpenApiResponse(
                response=ErrorResponseSerializer,
                description="Invalid credentials.",
                examples=[
                    OpenApiExample(
                        "Invalid credentials",
                        value={
                            "success": False,
                            "message": "Invalid credentials.",
                            "errors": {"detail": "Invalid phone or password."},
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
            "Authenticate with phone number and password. No auth required."
        ),
    )
    def post(self, request: Request, *args, **kwargs):
        try:
            # Validate data
            serializer = LoginSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            # Extract Data
            phone_number = serializer.validated_data["phoneNumber"]  # type: ignore
            password = serializer.validated_data["password"]  # type: ignore
            # Authenticate user via auth service
            user, access_token, refresh_token = AuthService.login(
                phone_number=phone_number, password=password
            )
            # Log and return response
            logger.info(f"User {user} logged in successfully via login api")
            return Response(
                data={
                    "success": True,
                    "result": {
                        "access": access_token,
                        "refresh": refresh_token,
                    },
                    "message": "User logged in successfully.",
                },
                status=status.HTTP_200_OK,
            )
        # Handle validation errors
        except ValidationError as ve:
            logger.warning(f"Invalid data in LoginAPIView: {serializer.errors}") # type: ignore
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
            logger.error(f"Exception in LoginAPIView: {e}")
            return Response(
                {
                    "success": False,
                    "message": "Unexpected error.",
                    "errors": {"detail": str(e)},
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


