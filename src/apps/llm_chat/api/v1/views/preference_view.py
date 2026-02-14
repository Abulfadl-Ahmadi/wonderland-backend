import logging
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.exceptions import ValidationError
from rest_framework.throttling import ScopedRateThrottle

from selectors_layer import LLMChatSelectors
from repositories import LLMChatRepository
from apps.llm_chat.models import LLMModel
from apps.llm_chat.api.v1.serializers import (
    UserLLMPreferenceSerializer,
    UserLLMPreferenceUpdateSerializer,
)

logger = logging.getLogger("app.v1.chat.preferences")


class UserLLMPreferenceAPIView(APIView):
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "put"]
    throttle_scope = "user"
    throttle_classes = [ScopedRateThrottle]

    def get(self, request: Request, *args, **kwargs):
        preference = LLMChatSelectors.get_user_preferences(request.user)
        if not preference:
            return Response(
                {
                    "success": True,
                    "result": {"preference": None},
                    "message": "Preferences retrieved successfully.",
                },
                status=status.HTTP_200_OK,
            )

        serializer = UserLLMPreferenceSerializer(preference)
        return Response(
            {
                "success": True,
                "result": {"preference": serializer.data},
                "message": "Preferences retrieved successfully.",
            },
            status=status.HTTP_200_OK,
        )

    def put(self, request: Request, *args, **kwargs):
        serializer = UserLLMPreferenceUpdateSerializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
            validated = serializer.validated_data
            default_model_id = validated.get("defaultModelId")
            if default_model_id is not None:
                exists = LLMModel.objects.filter(
                    id=default_model_id,
                    is_active=True,
                    provider__is_active=True,
                ).exists()
                if not exists:
                    return Response(
                        {
                            "success": False,
                            "message": "Validation error.",
                            "errors": {"defaultModelId": "Model not found."},
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            payload = {
                "default_model_id": default_model_id,
                "temperature": validated.get("temperature"),
                "top_p": validated.get("topP"),
                "max_tokens": validated.get("maxTokens"),
                "system_prompt": validated.get("systemPrompt"),
            }
            preference = LLMChatRepository.upsert_user_preferences(
                request.user, payload
            )
            response_serializer = UserLLMPreferenceSerializer(preference)
            return Response(
                {
                    "success": True,
                    "result": {"preference": response_serializer.data},
                    "message": "Preferences updated successfully.",
                },
                status=status.HTTP_200_OK,
            )
        except ValidationError as ve:
            return Response(
                {
                    "success": False,
                    "message": "Validation error.",
                    "errors": ve.get_full_details(),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as exc:
            logger.exception(f"Unexpected exception in preference update: {exc}")
            return Response(
                {
                    "success": False,
                    "message": "Unexpected error.",
                    "errors": {"detail": str(exc)},
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
