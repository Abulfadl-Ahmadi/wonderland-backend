from rest_framework import serializers

from apps.llm_chat.models import UserLLMPreference


class UserLLMPreferenceSerializer(serializers.ModelSerializer):
    defaultModel = serializers.SerializerMethodField()
    temperature = serializers.DecimalField(
        max_digits=4, decimal_places=3, required=False, allow_null=True
    )
    topP = serializers.DecimalField(
        source="top_p",
        max_digits=4,
        decimal_places=3,
        required=False,
        allow_null=True,
    )
    maxTokens = serializers.IntegerField(source="max_tokens", required=False, allow_null=True)
    systemPrompt = serializers.CharField(
        source="system_prompt", required=False, allow_blank=True
    )
    updatedAt = serializers.DateTimeField(source="updated_at", read_only=True)

    class Meta:
        model = UserLLMPreference
        fields = [
            "defaultModel",
            "temperature",
            "topP",
            "maxTokens",
            "systemPrompt",
            "updatedAt",
        ]

    def get_defaultModel(self, obj: UserLLMPreference) -> dict | None:
        if not obj.default_model:
            return None
        return {
            "id": obj.default_model.id,
            "name": obj.default_model.name,
            "slug": obj.default_model.slug,
        }


class UserLLMPreferenceUpdateSerializer(serializers.Serializer):
    defaultModelId = serializers.UUIDField(required=False, allow_null=True)
    temperature = serializers.DecimalField(
        max_digits=4, decimal_places=3, required=False, allow_null=True
    )
    topP = serializers.DecimalField(max_digits=4, decimal_places=3, required=False, allow_null=True)
    maxTokens = serializers.IntegerField(required=False, allow_null=True)
    systemPrompt = serializers.CharField(required=False, allow_blank=True)
