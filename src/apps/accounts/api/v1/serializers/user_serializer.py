from rest_framework import serializers

from services import UserService
from apps.accounts.models import UserModel
from .profile_serializer import ProfileSerializer
from .settings_serializer import SettingsSerializer


class UserSerializer(serializers.ModelSerializer):
    profile = ProfileSerializer(required=False)
    settings = SettingsSerializer(required=False)

    updatedAt = serializers.DateTimeField(read_only=True)
    createdAt = serializers.DateTimeField(read_only=True)

    password = serializers.CharField(write_only=True, required=False)
    confirmPassword = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = UserModel
        fields = [
            "id",
            "phone_number",
            "role",
            "updatedAt",
            "createdAt",
            "profile",
            "settings",
            "password",
            "confirmPassword",
        ]
        read_only_fields = [
            "id",
            "phone_number",
            "role",
            "status",
            "updatedAt",
            "createdAt",
        ]

    def validate(self, attrs):
        password = attrs.get("password", None)
        confirm_password = attrs.get("confirmPassword", None)

        if password and confirm_password and password != confirm_password:
            raise serializers.ValidationError(
                {"confirmPassword": "Passwords do not match."}, code="password_mismatch"
            )
        return attrs

    def update(self, instance, validated_data):
        profile_data = validated_data.pop("profile", None)
        settings_data = validated_data.pop("settings", None)

        password = validated_data.pop("password", None)
        confirm_password = validated_data.pop("confirmPassword", None)

        if validated_data:
            UserService.update_user(instance, validated_data)

        if profile_data:
            UserService.update_user_profile(instance, profile_data)

        if settings_data:
            UserService.update_user_settings(instance, settings_data)

        if password:
            UserService.update_user_password(instance, password)

        return instance