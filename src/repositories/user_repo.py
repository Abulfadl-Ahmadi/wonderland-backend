from typing import Optional
from django.utils import timezone

from constants import UserRole
from utils import normalize_iran_mobile
from apps.accounts.models import UserModel, Profile, Settings


class UserRepository:
    """
    Repository layer responsible for database operations related to Users,
    Profiles, and Settings.

    This layer isolates the ORM logic from business logic (services).
    """

    # ----------------------------------------------------------------------
    # CREATE METHODS
    # ----------------------------------------------------------------------

    @staticmethod
    def create_user(
        phone_number: str,
        role: UserRole = UserRole.USER,
        password=None,
    ) -> UserModel:
        """
        Create and return a new user.

        Args:
            phone_number (str): Phone number of the user (will be normalized).
            role (UserRole): User role enum value.
            password (str, optional): User password. Defaults to None.

        Returns:
            UserModel: The newly created user instance.
        """
        normalized_phone_number = normalize_iran_mobile(phone_number)

        # Create user WITHOUT setting password yet
        user = UserModel.objects.create(
            phone_number=normalized_phone_number,
            role=role,
        )

        # Handle password properly
        if password:
            user.set_password(password)  # ← This hashes it
        else:
            user.set_unusable_password()  # Optional: good practice for e.g. social login users

        user.save()  # Now save again with the hashed password

        return user

    @staticmethod
    def create_profile(
        user: UserModel, first_name: str, last_name: str, national_code: str
    ) -> Profile:
        """
        Create a profile associated with a user.

        Args:
            user (UserModel): The user instance.

        Returns:
            ProfileModel: The created profile.
        """
        profile = Profile.objects.create(
            user=user,
            first_name=first_name,
            last_name=last_name,
            national_code=national_code,
        )
        return profile

    @staticmethod
    def create_settings(user: UserModel) -> Settings:
        """
        Create settings associated with a user.

        Args:
            user (UserModel): The user instance.

        Returns:
            SettingsModel: The created settings object.
        """
        settings = Settings.objects.create(user=user)
        return settings

    # ----------------------------------------------------------------------
    # UPDATE METHODS
    # ----------------------------------------------------------------------

    @staticmethod
    def update_user(user: UserModel, **fields) -> UserModel:
        """
        Update user fields and persist changes.

        Args:
            user (UserModel): User instance to update.
            fields: Fields to update.

        Returns:
            UserModel: Updated user instance.
        """
        for key, value in fields.items():
            setattr(user, key, value)

        user.save(update_fields=list(fields.keys()))
        return user

    @staticmethod
    def update_profile(profile: Profile, **fields) -> Profile:
        """
        Update profile fields and persist changes.

        Args:
            profile (ProfileModel): Profile instance to update.
            fields: Fields to update.

        Returns:
            ProfileModel: Updated profile instance.
        """
        for key, value in fields.items():
            setattr(profile, key, value)

        profile.save(update_fields=list(fields.keys()))
        return profile

    @staticmethod
    def update_settings(settings: Settings, **fields) -> Settings:
        """
        Update settings fields and persist changes.

        Args:
            settings (SettingsModel): Settings instance to update.
            fields: Fields to update.

        Returns:
            SettingsModel: Updated settings instance.
        """
        for key, value in fields.items():
            setattr(settings, key, value)

        settings.save(update_fields=list(fields.keys()))
        return settings

    @staticmethod
    def update_user_password(user: UserModel, password: str) -> UserModel:
        """
        Update user password.

        Args:
            user (UserModel): User instance.
            password (str): New password.

        Returns:
            UserModel: Updated user instance.
        """
        user.set_password(password)
        user.save(update_fields=["password"])
        return user

    # ----------------------------------------------------------------------
    # GETTERS
    # ----------------------------------------------------------------------

    @staticmethod
    def get_user_by_phone_number(phone_number: str) -> Optional[UserModel]:
        """
        Retrieve a user by phone number.

        Args:
            phone_number (str): Phone number to search for.

        Returns:
            Optional[UserModel]: User instance if found, else None.
        """
        normalized_phone_number = normalize_iran_mobile(phone_number)
        user = UserModel.objects.filter(phone_number=normalized_phone_number).first()
        return user

    @staticmethod
    def get_user_profile(user: UserModel) -> Profile:
        """
        Retrieve the user's profile.

        Args:
            user (UserModel): User instance.

        Returns:
            ProfileModel: The user's profile.
        """

        profile = Profile.objects.get(user=user)
        return profile

    @staticmethod
    def get_user_settings(user: UserModel) -> Settings:
        """
        Retrieve the user's settings.

        Args:
            user (UserModel): User instance.

        Returns:
            SettingsModel: The user's settings.
        """

        settings = Settings.objects.get(user=user)
        return settings

    # ----------------------------------------------------------------------
    # UTILITIES
    # ----------------------------------------------------------------------

    @staticmethod
    def update_last_login(user: UserModel) -> None:
        """
        Update the last login timestamp for a user.

        Args:
            user (UserModel): User to update.
        """
        user.last_login = timezone.now()
        user.save(update_fields=["last_login"])
