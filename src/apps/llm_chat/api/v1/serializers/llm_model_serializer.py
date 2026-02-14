from rest_framework import serializers

from apps.llm_chat.models import LLMModel


class LLMModelListSerializer(serializers.ModelSerializer):
    contextWindow = serializers.IntegerField(source="context_window", read_only=True)
    inputCostPer1k = serializers.DecimalField(
        source="input_cost_per_1k",
        max_digits=12,
        decimal_places=6,
        allow_null=True,
        read_only=True,
    )
    outputCostPer1k = serializers.DecimalField(
        source="output_cost_per_1k",
        max_digits=12,
        decimal_places=6,
        allow_null=True,
        read_only=True,
    )
    isActive = serializers.BooleanField(source="is_active", read_only=True)
    provider = serializers.SerializerMethodField()

    class Meta:
        model = LLMModel
        fields = [
            "id",
            "provider",
            "name",
            "slug",
            "isActive",
            "contextWindow",
            "inputCostPer1k",
            "outputCostPer1k",
            "metadata",
        ]

    def get_provider(self, obj: LLMModel) -> dict:
        provider = obj.provider
        return {
            "id": provider.id,
            "name": provider.name,
            "slug": provider.slug,
        }
