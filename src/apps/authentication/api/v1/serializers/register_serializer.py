from rest_framework import serializers

from services import AuthService
from apps.accounts.models import UserModel


class RegisterSerializer(serializers.Serializer):
    """
    Serializer for registering a new user.
    """

    phoneNumber = serializers.CharField(
        required=True,
        error_messages={
            "required": "Phone number is required",
            "blank": "Phone number cannot be blank",
        },
    )

    password = serializers.CharField(
        required=True,
        write_only=True,
        style={"input_type": "password"},
        error_messages={
            "required": "Password is required",
            "blank": "Password cannot be blank",
        },
    )
    confirmPassword = serializers.CharField(
        required=True,
        write_only=True,
        style={"input_type": "password"},
        error_messages={
            "required": "Password confirmation is required",
            "blank": "Password confirmation cannot be blank",
        },
    )

    firstName = serializers.CharField(
        required=True,
        error_messages={
            "required": "First name is required",
            "blank": "First name cannot be blank",
        },
    )

    lastName = serializers.CharField(
        required=True,
        error_messages={
            "required": "Last name is required",
            "blank": "Last name cannot be blank",
        },
    )

    nationalCode = serializers.CharField(
        required=True,
        error_messages={
            "required": "National code is required",
            "blank": "National code cannot be blank",
        },
    )

    class Meta:
        model = UserModel
        fields = [
            "phoneNumber",
            "password",
            "confirmPassword",
            "firstName",
            "lastName",
            "nationalCode",
        ]

    def validate(self, attrs):
        password = attrs.get("password", None)
        confirm_password = attrs.get("confirmPassword", None)

        if password and confirm_password and password != confirm_password:
            raise serializers.ValidationError(
                {"confirmPassword": "Passwords do not match."}, code="password_mismatch"
            )
        return attrs

    def create(self, validated_data):
        phone_number = validated_data.get("phoneNumber")
        password = validated_data.get("password")
        confirm_password = validated_data.get("confirmPassword")

        first_name = validated_data.get("firstName")
        last_name = validated_data.get("lastName")
        national_code = validated_data.get("nationalCode")

        user = AuthService.register(
            first_name=first_name,
            last_name=last_name,
            national_code=national_code,
            phone_number=phone_number,
            password=password,
            confirm_password=confirm_password,
        )
        return user
