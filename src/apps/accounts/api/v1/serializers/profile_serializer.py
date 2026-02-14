from rest_framework import serializers
from apps.accounts.models import Profile


class ProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for ProfileModel.
    """

    lastName = serializers.CharField(
        source="last_name",
        required=True,
        min_length=2,
        max_length=30,
        error_messages={
            "required": "Last name is required",
            "min_length": "Last name must be at least 2 characters",
            "max_length": "Last name must be at most 30 characters",
        },
    )

    firstName = serializers.CharField(
        source="first_name",
        required=True,
        min_length=2,
        max_length=30,
        error_messages={
            "required": "First name is required",
            "min_length": "First name must be at least 2 characters",
            "max_length": "First name must be at most 30 characters",
        },
    )

    nationalCode = serializers.CharField(
        source="national_code",
        required=True,
        min_length=10,
        max_length=10,
        error_messages={
            "required": "National code is required",
            "min_length": "National code must be at least 10 characters",
            "max_length": "National code must be at most 10 characters",
        },
    )


    class Meta:
        model = Profile

        fields = [
            "lastName",
            "firstName",
            "nationalCode",
        ]

        read_only_fields = [
            "id",
            "user",
            "updated_at",
            "created_at",
        ]

