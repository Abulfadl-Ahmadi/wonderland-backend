from decimal import Decimal
from typing import Any, Mapping, Optional

from django.utils import timezone

from common.exceptions import DomainError
from apps.llm_chat.models import (
    Conversation,
    LLMModel,
    Message,
    MessageRole,
    UserLLMPreference,
)


class LLMChatRepository:
    """
    Repository layer responsible for database operations related to LLM chat.

    This layer isolates ORM logic from business logic (services).
    """

    # ------------------------------------------------------------------
    # CREATE / UPDATE METHODS
    # ------------------------------------------------------------------

    @staticmethod
    def create_conversation(user, title: Optional[str] = None) -> Conversation:
        """
        Create and return a new conversation for the given user.

        Args:
            user: User instance.
            title: Optional conversation title.

        Returns:
            Conversation: The created conversation.
        """
        return Conversation.objects.create(user=user, title=title or "")

    @staticmethod
    def archive_or_rename_conversation(
        conversation: Conversation,
        title: Optional[str] = None,
        is_archived: Optional[bool] = None,
        user=None,
    ) -> Conversation:
        """
        Update conversation title and/or archive status.

        Pass user to enforce ownership.
        """
        if user is not None:
            LLMChatRepository._assert_conversation_owner(conversation, user)

        fields: dict[str, Any] = {}
        if title is not None:
            conversation.title = title
            fields["title"] = title
        if is_archived is not None:
            conversation.is_archived = is_archived
            fields["is_archived"] = is_archived

        if fields:
            conversation.updated_at = timezone.now()
            fields["updated_at"] = conversation.updated_at
            conversation.save(update_fields=list(fields.keys()))
        return conversation

    @staticmethod
    def create_user_message(
        conversation: Conversation,
        content: str,
        user=None,
    ) -> Message:
        """
        Create a user message within a conversation.

        Pass user to enforce ownership.
        """
        if user is not None:
            LLMChatRepository._assert_conversation_owner(conversation, user)

        message = Message.objects.create(
            conversation=conversation,
            role=MessageRole.USER,
            content=content,
        )
        LLMChatRepository._touch_conversation(conversation)
        return message

    @staticmethod
    def create_assistant_message(
        conversation: Conversation,
        content: str,
        model_used: Optional[LLMModel] = None,
        usage: Optional[Mapping[str, Any]] = None,
        cost: Optional[Mapping[str, Any]] = None,
        raw_response: Optional[Mapping[str, Any]] = None,
        error: Optional[Mapping[str, Any]] = None,
        user=None,
    ) -> Message:
        """
        Create an assistant message and store usage, cost, and error data.

        Pass user to enforce ownership.
        """
        if user is not None:
            LLMChatRepository._assert_conversation_owner(conversation, user)

        usage_data = usage or {}
        cost_data = cost or {}
        error_data = error or {}

        message = Message.objects.create(
            conversation=conversation,
            role=MessageRole.ASSISTANT,
            content=content,
            model_used=model_used,
            raw_response=raw_response,
            error_code=error_data.get("code"),
            error_message=error_data.get("message"),
            prompt_tokens=usage_data.get("prompt_tokens"),
            completion_tokens=usage_data.get("completion_tokens"),
            total_tokens=usage_data.get("total_tokens"),
            input_cost=LLMChatRepository._to_decimal(cost_data.get("input_cost")),
            output_cost=LLMChatRepository._to_decimal(cost_data.get("output_cost")),
            total_cost=LLMChatRepository._to_decimal(cost_data.get("total_cost")),
        )
        LLMChatRepository._touch_conversation(conversation)
        return message

    @staticmethod
    def upsert_user_preferences(user, payload: Mapping[str, Any]) -> UserLLMPreference:
        """
        Create or update user LLM preferences.
        """
        defaults: dict[str, Any] = {
            key: value
            for key, value in payload.items()
            if key
            in {
                "default_model",
                "default_model_id",
                "temperature",
                "top_p",
                "max_tokens",
                "system_prompt",
            }
        }

        if "default_model_id" in defaults and "default_model" not in defaults:
            defaults["default_model_id"] = defaults.pop("default_model_id")

        preferences, _ = UserLLMPreference.objects.update_or_create(
            user=user,
            defaults=defaults,
        )
        return preferences

    # ------------------------------------------------------------------
    # INTERNAL HELPERS
    # ------------------------------------------------------------------

    @staticmethod
    def _assert_conversation_owner(conversation: Conversation, user) -> None:
        if conversation.user_id != user.id:
            raise DomainError("Conversation does not belong to the user.")

    @staticmethod
    def _touch_conversation(conversation: Conversation) -> None:
        conversation.updated_at = timezone.now()
        conversation.save(update_fields=["updated_at"])

    @staticmethod
    def _to_decimal(value: Any) -> Optional[Decimal]:
        if value is None:
            return None
        if isinstance(value, Decimal):
            return value
        try:
            return Decimal(str(value))
        except Exception:
            return None
