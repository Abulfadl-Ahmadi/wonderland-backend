from rest_framework import serializers

from apps.llm_chat.models import Conversation, Message


class ConversationListSerializer(serializers.ModelSerializer):
    isArchived = serializers.BooleanField(source="is_archived", read_only=True)
    updatedAt = serializers.DateTimeField(source="updated_at", read_only=True)
    createdAt = serializers.DateTimeField(source="created_at", read_only=True)
    lastMessagePreview = serializers.SerializerMethodField()
    lastMessageAt = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = [
            "id",
            "title",
            "isArchived",
            "updatedAt",
            "createdAt",
            "lastMessagePreview",
            "lastMessageAt",
        ]

    def get_lastMessagePreview(self, obj: Conversation) -> str | None:
        message = self._get_last_message(obj)
        if not message:
            return None
        return message.content[:200]

    def get_lastMessageAt(self, obj: Conversation):
        message = self._get_last_message(obj)
        return message.created_at if message else None

    def _get_last_message(self, obj: Conversation) -> Message | None:
        if hasattr(obj, "last_message_list") and obj.last_message_list:
            return obj.last_message_list[0]
        return (
            obj.messages.order_by("-created_at").only("content", "created_at").first()
        )


class ConversationDetailSerializer(ConversationListSerializer):
    pass


class ConversationCreateSerializer(serializers.Serializer):
    title = serializers.CharField(required=False, allow_blank=True, max_length=255)


class ConversationUpdateSerializer(serializers.Serializer):
    title = serializers.CharField(required=False, allow_blank=True, max_length=255)
    isArchived = serializers.BooleanField(required=False)
