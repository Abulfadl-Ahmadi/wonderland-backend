import logging
from decimal import Decimal
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.exceptions import ValidationError
from rest_framework.throttling import ScopedRateThrottle

from common.pagination import DefaultPagination
from common.exceptions import OpenRouterError
from selectors_layer import LLMChatSelectors
from repositories import LLMChatRepository
from services import OpenRouterService
from apps.llm_chat.api.v1.serializers import (
    MessageSerializer,
    MessageCreateSerializer,
)

logger = logging.getLogger("app.v1.chat.messages")


class MessageListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post"]
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

        paginator = DefaultPagination()
        messages = LLMChatSelectors.list_messages(
            conversation, pagination=(paginator, request)
        )
        serializer = MessageSerializer(messages, many=True)
        return Response(
            {
                "success": True,
                "result": {
                    "count": paginator.page.paginator.count,
                    "next": paginator.get_next_link(),
                    "previous": paginator.get_previous_link(),
                    "messages": serializer.data,
                },
                "message": "Messages retrieved successfully.",
            },
            status=status.HTTP_200_OK,
        )

    def post(self, request: Request, conversation_id: str, *args, **kwargs):
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

        serializer = MessageCreateSerializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
            content = serializer.validated_data["content"]

            user_message = LLMChatRepository.create_user_message(
                conversation=conversation,
                content=content,
                user=request.user,
            )

            preference = LLMChatSelectors.get_user_preferences(request.user)
            model_used = self._resolve_model(preference)
            temperature = preference.temperature if preference else None
            top_p = preference.top_p if preference else None
            max_tokens = preference.max_tokens if preference else None
            system_prompt = preference.system_prompt if preference else None

            if not model_used:
                model_used = LLMChatSelectors.list_active_models().first()

            if not model_used:
                return Response(
                    {
                        "success": False,
                        "message": "No active models available.",
                        "errors": {"detail": "No active models available."},
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            messages_context = []
            if system_prompt:
                messages_context.append({"role": "system", "content": system_prompt})

            history = LLMChatSelectors.list_messages(conversation)
            for item in history:
                messages_context.append({"role": item.role, "content": item.content})

            try:
                result = OpenRouterService.chat_completion(
                    model_slug=model_used.slug,
                    messages=messages_context,
                    temperature=float(temperature) if temperature is not None else None,
                    top_p=float(top_p) if top_p is not None else None,
                    max_tokens=max_tokens,
                )
                assistant_text = result.get("assistant_text", "")
                usage = result.get("usage") or {}
                raw = result.get("raw")
                cost = self._compute_costs(model_used, usage)

                assistant_message = LLMChatRepository.create_assistant_message(
                    conversation=conversation,
                    content=assistant_text,
                    model_used=model_used,
                    usage=usage,
                    cost=cost,
                    raw_response=raw,
                    error=None,
                    user=request.user,
                )

                response_serializer = MessageSerializer(assistant_message)
                return Response(
                    {
                        "success": True,
                        "result": {"message": response_serializer.data},
                        "message": "Message created successfully.",
                    },
                    status=status.HTTP_200_OK,
                )

            except OpenRouterError as exc:
                error_payload = {
                    "code": exc.error_code or "openrouter_error",
                    "message": str(exc),
                }
                assistant_message = LLMChatRepository.create_assistant_message(
                    conversation=conversation,
                    content="",
                    model_used=model_used,
                    usage=None,
                    cost=None,
                    raw_response=exc.raw,
                    error=error_payload,
                    user=request.user,
                )
                response_serializer = MessageSerializer(assistant_message)
                return Response(
                    {
                        "success": False,
                        "result": {"message": response_serializer.data},
                        "message": "OpenRouter request failed.",
                        "errors": {"detail": str(exc)},
                    },
                    status=status.HTTP_502_BAD_GATEWAY,
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
            logger.exception(f"Unexpected exception in message create: {exc}")
            return Response(
                {
                    "success": False,
                    "message": "Unexpected error.",
                    "errors": {"detail": str(exc)},
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @staticmethod
    def _compute_costs(model_used, usage: dict) -> dict | None:
        if not usage:
            return None

        prompt_tokens = usage.get("prompt_tokens")
        completion_tokens = usage.get("completion_tokens")

        input_cost = None
        output_cost = None

        if model_used and model_used.input_cost_per_1k and prompt_tokens is not None:
            input_cost = (
                Decimal(str(prompt_tokens))
                * model_used.input_cost_per_1k
                / Decimal(1000)
            )
        if (
            model_used
            and model_used.output_cost_per_1k
            and completion_tokens is not None
        ):
            output_cost = (
                Decimal(str(completion_tokens))
                * model_used.output_cost_per_1k
                / Decimal(1000)
            )

        total_cost = None
        if input_cost is not None or output_cost is not None:
            total_cost = (input_cost or Decimal("0")) + (output_cost or Decimal("0"))

        return {
            "input_cost": input_cost,
            "output_cost": output_cost,
            "total_cost": total_cost,
        }

    @staticmethod
    def _resolve_model(preference):
        if not preference or not preference.default_model:
            return None
        model = preference.default_model
        if not model.is_active or not model.provider.is_active:
            return None
        return model
