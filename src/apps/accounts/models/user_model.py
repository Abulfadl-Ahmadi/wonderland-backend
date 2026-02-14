import uuid
from django.db import models
from django.core.exceptions import ValidationError
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin

from .user_manager import UserManager
from utils import normalize_iran_mobile
from constants import UserRole, UserStatus


class UserModel(AbstractBaseUser, PermissionsMixin):
    """
    Custom user model that replaces Django's default user model.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    phone_number = models.CharField(
        max_length=11,  # 09 + 9 digits
        unique=True,
        db_index=True,
        help_text="Iran mobile in national format, e.g. 09123456789",
    )

    # Status for the user (active, banned, deleted)
    status = models.CharField(
        max_length=20,
        choices=UserStatus.choices,
        default=UserStatus.ACTIVE,
        db_index=True,
    )
    # Role for the user (admin, user, menu owner)
    role = models.CharField(
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.USER,
        db_index=True,
    )
    # Timestamps for user creation and last update
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # Attach the custom manager
    objects = UserManager()

    # Set the USERNAME_FIELD to 'phone_number'
    USERNAME_FIELD = "phone_number"

    class Meta:
        """Meta class for the UserModel."""

        verbose_name = "User Account"
        verbose_name_plural = "User Accounts"
        ordering = ("-created_at",)

    def __str__(self) -> str:
        """String representation of the user."""
        return self.phone_number

    @property
    def is_staff(self) -> bool:
        """Check if the user is staff."""
        status: bool = (
            self.is_superuser
            or self.role == UserRole.ADMIN
            or self.role == UserRole.SUPERUSER
        )
        return status

    @property
    def is_active(self) -> bool:
        """Check if the user status is active."""
        return self.status == UserStatus.ACTIVE

    def clean(self):
        """
        Ensures phone_number is normalized and valid.
        Django admin + model validation calls this.
        """
        super().clean()
        try:
            self.phone_number = normalize_iran_mobile(self.phone_number)
        except ValidationError as e:
            raise ValidationError("Invalid phone number: " + str(e))

    def save(self, *args, **kwargs):
        """
        Normalizes even if .clean() isn't called (e.g. programmatic saves).
        """
        if self.phone_number:
            self.phone_number = normalize_iran_mobile(self.phone_number)
        return super().save(*args, **kwargs)
    