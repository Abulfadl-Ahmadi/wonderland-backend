from utils import normalize_iran_mobile
from constants import UserRole, UserStatus

from django.contrib.auth.models import BaseUserManager


class UserManager(BaseUserManager):
    """Custom manager for the UserModel, handling user and superuser creation."""

    def create_user(self, phone_number, password=None, **extra_fields):
        """Create a new user with the given phone number and password."""

        if not phone_number:
            raise ValueError("Users must have a phone number.")

        # Normalize phone number
        phone_number = normalize_iran_mobile(phone_number)

        user = self.model(
            phone_number=phone_number,
            is_superuser=False,
            role=UserRole.USER,
            status=UserStatus.ACTIVE,
            **extra_fields
        )

        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()  # for OAuth cases

        user.save(using=self._db)

        return user

    def create_superuser(self, phone_number, password=None, **extra_fields):
        """Create a new superuser with the given phone number and password."""
        user = self.create_user(
            phone_number=phone_number, password=password, **extra_fields
        )

        # Set the user role to admin and status to active
        user.is_superuser = True
        user.role = UserRole.SUPERUSER
        user.status = UserStatus.ACTIVE

        user.save(using=self._db)

        return user
    