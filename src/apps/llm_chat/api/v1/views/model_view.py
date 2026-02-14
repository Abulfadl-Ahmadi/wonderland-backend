import logging
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.throttling import ScopedRateThrottle

from selectors_layer import LLMChatSelectors
from apps.llm_chat.api.v1.serializers import LLMModelListSerializer

logger = logging.getLogger("app.v1.chat.models")


class LLMModelListAPIView(APIView):
    permission_classes = [IsAuthenticated]
    http_method_names = ["get"]
    throttle_scope = "user"
    throttle_classes = [ScopedRateThrottle]

    def get(self, request: Request, *args, **kwargs):
        models = LLMChatSelectors.list_active_models()
        serializer = LLMModelListSerializer(models, many=True)
        logger.info("User requested LLM models list")
        return Response(
            {
                "success": True,
                "result": {"models": serializer.data},
                "message": "LLM models retrieved successfully.",
            },
            status=status.HTTP_200_OK,
        )
