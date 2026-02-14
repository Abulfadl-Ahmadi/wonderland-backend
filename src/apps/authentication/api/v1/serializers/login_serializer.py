from rest_framework import serializers


class LoginSerializer(serializers.Serializer):
    """
    Serializer for authenticating a user.
    """

    phoneNumber = serializers.CharField(
        required=True,
        min_length=11,
        max_length=11,
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
