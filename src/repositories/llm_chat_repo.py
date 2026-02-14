from decimal import Decimal
from typing import Any, Mapping, Optional

from django.utils import timezone
from django.db import transaction

from common.exceptions import DomainError
from apps.llm_chat.models import (
    Conversation,
    LLMModel,
    Message,
    MessageRole,
    MessageStatus,
    UserLLMPreference,
    UserProviderCredential,
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
    def create_streaming_message(
        conversation: Conversation,
        model_used: Optional[LLMModel] = None,
        credential_used: Optional[UserProviderCredential] = None,
        user=None,
    ) -> Message:
        """
        Create an assistant message with status=STREAMING and empty content.

        Phase 1 of two-phase persistence: creates the message immediately so client
        can track it by ID while tokens are being streamed.

        Pass user to enforce ownership.

        Args:
            conversation: The conversation to add the message to.
            model_used: The LLM model used for this response.
            credential_used: The credential/API key used.
            user: User instance (for ownership check).

        Returns:
            Message: The created message with status=STREAMING.
        """
        if user is not None:
            LLMChatRepository._assert_conversation_owner(conversation, user)

        message = Message.objects.create(
            conversation=conversation,
            role=MessageRole.ASSISTANT,
            content="",  # Empty during streaming
            status=MessageStatus.STREAMING,
            model_used=model_used,
            credential_used=credential_used,
        )
        LLMChatRepository._touch_conversation(conversation)
        return message

    @staticmethod
    def update_streaming_message_completed(
        message: Message,
        content: str,
        usage: Optional[Mapping[str, Any]] = None,
        cost: Optional[Mapping[str, Any]] = None,
        raw_response: Optional[Mapping[str, Any]] = None,
        user=None,
    ) -> Message:
        """
        Update a STREAMING message to COMPLETED with final content and usage.

        Phase 2 of two-phase persistence: atomically finalizes the message
        after streaming completes.

        Uses select_for_update() to prevent race conditions.

        Pass user to enforce ownership.

        Args:
            message: The message to update (must have status=STREAMING).
            content: The final message content.
            usage: Dict with prompt_tokens, completion_tokens, total_tokens.
            cost: Dict with input_cost, output_cost, total_cost.
            raw_response: The raw API response from the provider.
            user: User instance (for ownership check).

        Returns:
            Message: The updated message with status=COMPLETED.
        """
        if user is not None:
            if message.conversation.user_id != user.id:
                raise DomainError("Message does not belong to the user.")

        usage_data = usage or {}
        cost_data = cost or {}

        with transaction.atomic():
            # Lock the message row to prevent concurrent updates
            message = Message.objects.select_for_update().get(id=message.id)
            
            message.content = content
            message.status = MessageStatus.COMPLETED
            message.raw_response = raw_response
            message.prompt_tokens = usage_data.get("prompt_tokens")
            message.completion_tokens = usage_data.get("completion_tokens")
            message.total_tokens = usage_data.get("total_tokens")
            message.input_cost = LLMChatRepository._to_decimal(cost_data.get("input_cost"))
            message.output_cost = LLMChatRepository._to_decimal(cost_data.get("output_cost"))
            message.total_cost = LLMChatRepository._to_decimal(cost_data.get("total_cost"))
            message.updated_at = timezone.now()
            
            message.save(
                update_fields=[
                    "content",
                    "status",
                    "raw_response",
                    "prompt_tokens",
                    "completion_tokens",
                    "total_tokens",
                    "input_cost",
                    "output_cost",
                    "total_cost",
                    "updated_at",
                ]
            )

        LLMChatRepository._touch_conversation(message.conversation)
        return message

    @staticmethod
    def update_streaming_message_error(
        message: Message,
        error_code: str,
        error_message: str,
        raw_response: Optional[Mapping[str, Any]] = None,
        user=None,
    ) -> Message:
        """
        Update a STREAMING message to ERROR with error details.

        Phase 2 of two-phase persistence: atomically marks the message as failed
        after streaming error occurs.

        Uses select_for_update() to prevent race conditions.

        Pass user to enforce ownership.

        Args:
            message: The message to update (must have status=STREAMING).
            error_code: Error code/identifier (e.g., "openrouter_timeout").
            error_message: Human-readable error message.
            raw_response: The raw error response from the provider.
            user: User instance (for ownership check).

        Returns:
            Message: The updated message with status=ERROR.
        """
        if user is not None:
            if message.conversation.user_id != user.id:
                raise DomainError("Message does not belong to the user.")

        with transaction.atomic():
            # Lock the message row to prevent concurrent updates
            message = Message.objects.select_for_update().get(id=message.id)
            
            message.status = MessageStatus.ERROR
            message.error_code = error_code
            message.error_message = error_message
            message.raw_response = raw_response
            message.updated_at = timezone.now()
            
            message.save(
                update_fields=[
                    "status",
                    "error_code",
                    "error_message",
                    "raw_response",
                    "updated_at",
                ]
            )

        LLMChatRepository._touch_conversation(message.conversation)
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
