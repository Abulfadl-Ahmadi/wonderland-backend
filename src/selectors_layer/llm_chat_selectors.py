from typing import Any, Optional, Tuple

from django.db.models import Prefetch

from apps.llm_chat.models import Conversation, LLMModel, Message, UserLLMPreference


class LLMChatSelectors:
    """
    Selector class for LLM chat read operations.
    """

    @staticmethod
    def list_active_models():
        return (
            LLMModel.objects.filter(is_active=True, provider__is_active=True)
            .select_related("provider")
            .order_by("provider__name", "name")
        )

    @staticmethod
    def list_user_conversations(user, pagination=None):
        last_message_prefetch = Prefetch(
            "messages",
            queryset=Message.objects.order_by("-created_at")[:1],
            to_attr="last_message_list",
        )
        queryset = (
            Conversation.objects.filter(user=user)
            .select_related("user")
            .prefetch_related(last_message_prefetch)
            .order_by("-updated_at")
        )
        return LLMChatSelectors._paginate_queryset(queryset, pagination)

    @staticmethod
    def get_user_conversation_detail(user, conversation_id) -> Optional[Conversation]:
        last_message_prefetch = Prefetch(
            "messages",
            queryset=Message.objects.order_by("-created_at")[:1],
            to_attr="last_message_list",
        )
        return (
            Conversation.objects.filter(user=user, id=conversation_id)
            .select_related("user")
            .prefetch_related(last_message_prefetch)
            .first()
        )

    @staticmethod
    def list_messages(conversation: Conversation, pagination=None):
        queryset = (
            Message.objects.filter(conversation=conversation)
            .select_related("model_used", "conversation")
            .order_by("created_at")
        )
        return LLMChatSelectors._paginate_queryset(queryset, pagination)

    @staticmethod
    def get_user_preferences(user) -> Optional[UserLLMPreference]:
        return (
            UserLLMPreference.objects.filter(user=user)
            .select_related("default_model")
            .first()
        )

    # ------------------------------------------------------------------
    # INTERNAL HELPERS
    # ------------------------------------------------------------------

    @staticmethod
    def _paginate_queryset(queryset, pagination):
        if pagination is None:
            return queryset

        if isinstance(pagination, Tuple) and len(pagination) == 2:
            paginator, request = pagination
            return paginator.paginate_queryset(queryset, request)

        if hasattr(pagination, "paginate_queryset") and hasattr(pagination, "request"):
            return pagination.paginate_queryset(queryset, pagination.request)

        return queryset
