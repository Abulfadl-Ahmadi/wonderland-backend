from rest_framework import serializers

from apps.llm_chat.models import Message


class MessageSerializer(serializers.ModelSerializer):
    modelUsed = serializers.SerializerMethodField()
    createdAt = serializers.DateTimeField(source="created_at", read_only=True)
    promptTokens = serializers.IntegerField(
        source="prompt_tokens", read_only=True, allow_null=True
    )
    completionTokens = serializers.IntegerField(
        source="completion_tokens", read_only=True, allow_null=True
    )
    totalTokens = serializers.IntegerField(
        source="total_tokens", read_only=True, allow_null=True
    )
    inputCost = serializers.DecimalField(
        source="input_cost",
        max_digits=12,
        decimal_places=6,
        allow_null=True,
        read_only=True,
    )
    outputCost = serializers.DecimalField(
        source="output_cost",
        max_digits=12,
        decimal_places=6,
        allow_null=True,
        read_only=True,
    )
    totalCost = serializers.DecimalField(
        source="total_cost",
        max_digits=12,
        decimal_places=6,
        allow_null=True,
        read_only=True,
    )
    errorCode = serializers.CharField(source="error_code", read_only=True)
    errorMessage = serializers.CharField(source="error_message", read_only=True)

    class Meta:
        model = Message
        fields = [
            "id",
            "role",
            "content",
            "createdAt",
            "modelUsed",
            "promptTokens",
            "completionTokens",
            "totalTokens",
            "inputCost",
            "outputCost",
            "totalCost",
            "errorCode",
            "errorMessage",
        ]

    def get_modelUsed(self, obj: Message) -> dict | None:
        if not obj.model_used:
            return None
        return {
            "id": obj.model_used.id,
            "name": obj.model_used.name,
            "slug": obj.model_used.slug,
        }


class MessageCreateSerializer(serializers.Serializer):
    content = serializers.CharField(min_length=1)
