from rest_framework import serializers
from apps.accounts.models import Settings
from constants import UserTheme, UserLanguage


class SettingsSerializer(serializers.ModelSerializer):
    """
    Serializer for SettingsModel.
    """

    theme = serializers.ChoiceField(
        choices=UserTheme.choices,
        error_messages={
            "required": "Theme is required",
            "blank": "Theme cannot be blank",
            "invalid_choice": "Invalid theme",
        },
    )

    language = serializers.ChoiceField(
        choices=UserLanguage.choices,
        error_messages={
            "required": "Language is required",
            "blank": "Language cannot be blank",
            "invalid_choice": "Invalid language",
        },
    )

    class Meta:
        model = Settings
        fields = [
            "theme",
            "language",
        ]
        read_only_fields = [
            "id",
            "user",
            "updated_at",
            "created_at",
        ]