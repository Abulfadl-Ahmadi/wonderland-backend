from django.db import transaction
from rest_framework.exceptions import ValidationError


from constants import UserRole
from repositories import UserRepository
from apps.accounts.models import UserModel


class UserService:
    """
    Service layer for user-related business logic.
    Handles:
        - Creating users
        - Creating related objects (profile, settings)
        - Validations for unique phone_number
    """

    @staticmethod
    @transaction.atomic
    def create_user(
        phone_number: str, role: UserRole = UserRole.USER, **extra_fields
    ) -> UserModel:
        """
        Create a fully initialized user:
            - user record
            - profile entry
            - settings entry

        Args:
            phone_number (str): User phone number.
            role (UserRole): Assigned user role (default: UserRole.USER).
            extra_fields: Additional fields passed to user creation.

        Returns:
            UserModel: The newly created user instance.

        Raises:
            ValidationError:
                - user_exists: If a user with the given phone_number already exists.
        """

        # Ensure unique phone_number
        existing_user = UserRepository.get_user_by_phone_number(phone_number)
        if existing_user:
            raise ValidationError(
                {"phone_number": "A user with this phone number already exists."},
                code="user_exists",
            )

        # Create main user
        new_user = UserRepository.create_user(
            phone_number=phone_number,
            role=role,
            password=extra_fields.get("password", ""),
        )

        # Create related objects (decoupled via repository)
        user_profile = UserRepository.create_profile(
            new_user,
            first_name=extra_fields.get("first_name", ""),
            last_name=extra_fields.get("last_name", ""),
            national_code=extra_fields.get("national_code", ""),
        )
        user_settings = UserRepository.create_settings(new_user)

        new_user.refresh_from_db()
        return new_user

    @staticmethod
    @transaction.atomic
    def update_user(user: UserModel, user_data: dict = {}) -> UserModel:
        """
        Update user, profile, and settings safely.

        Args:
            user (UserModel): The user being updated.
            user_data (dict): Fields for UserModel.

        Returns:
            UserModel: updated user instance.
        """

        # Clean data by removing fields not allowed
        cleaned = UserService._clean_data(
            user_data or {},
            [
                "id",
                "status",
                "role",
                "phone_number",
                "password",
                "created_at",
                "updated_at",
            ],
        )

        # Update user
        if cleaned:
            UserRepository.update_user(user, **cleaned)
            user.refresh_from_db()

        return user

    @staticmethod
    @transaction.atomic
    def update_user_profile(user: UserModel, profile_data: dict = {}) -> UserModel:
        """
        Update user profile.

        Args:
            user (UserModel): User instance.
            profile_data (dict): Fields for ProfileModel.

        Returns:
            UserModel: Updated user instance.
            ProfileModel: Updated profile instance.
        """

        # Clean data by removing fields not allowed
        cleaned = UserService._clean_data(
            profile_data or {},
            ["id", "user", "created_at", "updated_at"],
        )

        # Update profile
        if cleaned:
            profile = UserRepository.get_user_profile(user)
            UserRepository.update_profile(profile, **cleaned)
            user.refresh_from_db()

        return user

    @staticmethod
    @transaction.atomic
    def update_user_settings(user: UserModel, settings_data: dict = {}) -> UserModel:
        """
        Update user settings.

        Args:
            user (UserModel): User instance.
            settings_data (dict): Fields for SettingsModel.

        Returns:
            UserModel: Updated user instance.
            SettingsModel: Updated settings instance.
        """

        # Clean data by removing fields not allowed
        cleaned = UserService._clean_data(
            settings_data or {},
            ["id", "user", "created_at", "updated_at"],
        )

        # Update settings
        if cleaned:
            settings = UserRepository.get_user_settings(user)
            UserRepository.update_settings(settings, **cleaned)
            user.refresh_from_db()

        return user

    @staticmethod
    @transaction.atomic
    def update_user_password(user: UserModel, password: str) -> UserModel:
        """
        Update user password.

        Args:
            user (UserModel): User instance.
            password (str): New password.

        Returns:
            UserModel: Updated user instance.
        """
        UserRepository.update_user_password(user, password)
        user.refresh_from_db()
        return user

    # -------------------------
    # Internal utility methods
    # -------------------------
    @staticmethod
    def _clean_data(data: dict, disallowed_fields: list[str]) -> dict:
        """
        Clean data from disallowed fields.

        Args:
            data (dict): Data to clean.
            disallowed_fields (list[str]): List of disallowed fields.

        Returns:
            dict: Cleaned data.
        """
        if not data:
            return {}

        return {
            key: value for key, value in data.items() if key not in disallowed_fields
        }
