import logging
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.exceptions import ValidationError
from rest_framework.throttling import ScopedRateThrottle

from common.pagination import DefaultPagination
from selectors_layer import LLMChatSelectors
from repositories import LLMChatRepository
from apps.llm_chat.api.v1.serializers import (
    ConversationListSerializer,
    ConversationDetailSerializer,
    ConversationCreateSerializer,
    ConversationUpdateSerializer,
)

logger = logging.getLogger("app.v1.chat.conversations")


class ConversationListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post"]
    throttle_scope = "user"
    throttle_classes = [ScopedRateThrottle]

    def get(self, request: Request, *args, **kwargs):
        paginator = DefaultPagination()
        conversations = LLMChatSelectors.list_user_conversations(
            request.user, pagination=(paginator, request)
        )
        serializer = ConversationListSerializer(conversations, many=True)
        return Response(
            {
                "success": True,
                "result": {
                    "count": paginator.page.paginator.count,
                    "next": paginator.get_next_link(),
                    "previous": paginator.get_previous_link(),
                    "conversations": serializer.data,
                },
                "message": "Conversations retrieved successfully.",
            },
            status=status.HTTP_200_OK,
        )

    def post(self, request: Request, *args, **kwargs):
        serializer = ConversationCreateSerializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
            title = serializer.validated_data.get("title", "")
            conversation = LLMChatRepository.create_conversation(request.user, title)
            response_serializer = ConversationDetailSerializer(conversation)
            return Response(
                {
                    "success": True,
                    "result": {"conversation": response_serializer.data},
                    "message": "Conversation created successfully.",
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
            logger.exception(f"Unexpected exception in conversation create: {exc}")
            return Response(
                {
                    "success": False,
                    "message": "Unexpected error.",
                    "errors": {"detail": str(exc)},
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ConversationDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "patch"]
    throttle_scope = "user"
    throttle_classes = [ScopedRateThrottle]

    def get(self, request: Request, conversation_id: str, *args, **kwargs):
        conversation = LLMChatSelectors.get_user_conversation_detail(
            request.user, conversation_id
        )
        if not conversation:
            return Response(
                {
                    "success": False,
                    "message": "Conversation not found.",
                    "errors": {"detail": "Conversation not found."},
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = ConversationDetailSerializer(conversation)
        return Response(
            {
                "success": True,
                "result": {"conversation": serializer.data},
                "message": "Conversation retrieved successfully.",
            },
            status=status.HTTP_200_OK,
        )

    def patch(self, request: Request, conversation_id: str, *args, **kwargs):
        conversation = LLMChatSelectors.get_user_conversation_detail(
            request.user, conversation_id
        )
        if not conversation:
            return Response(
                {
                    "success": False,
                    "message": "Conversation not found.",
                    "errors": {"detail": "Conversation not found."},
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = ConversationUpdateSerializer(data=request.data, partial=True)
        try:
            serializer.is_valid(raise_exception=True)
            title = serializer.validated_data.get("title")
            is_archived = serializer.validated_data.get("isArchived")
            updated = LLMChatRepository.archive_or_rename_conversation(
                conversation,
                title=title,
                is_archived=is_archived,
                user=request.user,
            )
            response_serializer = ConversationDetailSerializer(updated)
            return Response(
                {
                    "success": True,
                    "result": {"conversation": response_serializer.data},
                    "message": "Conversation updated successfully.",
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
            logger.exception(f"Unexpected exception in conversation update: {exc}")
            return Response(
                {
                    "success": False,
                    "message": "Unexpected error.",
                    "errors": {"detail": str(exc)},
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
