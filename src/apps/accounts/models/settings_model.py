import uuid
from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from constants import UserLanguage, UserTheme

UserModel = get_user_model()


class Settings(models.Model):
    """
    Model for storing user settings data.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # One-to-one relationship with UserModel
    user = models.OneToOneField(
        UserModel, on_delete=models.CASCADE, related_name="settings", db_index=True
    )
    # Theme & Appearance
    theme = models.CharField(
        max_length=10, choices=UserTheme.choices, default=UserTheme.SYSTEM
    )
    language = models.CharField(
        max_length=20, choices=UserLanguage.choices, default=UserLanguage.PERSIAN
    )
    # Timestamps
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.phone_number}'s settings"  # type: ignore

    class Meta:
        verbose_name = "User Setting"
        verbose_name_plural = "User Settings"

    def clean(self) -> None:
        """Validate theme and language values."""
        if self.theme not in UserTheme.values:
            raise ValidationError({"theme": f"Invalid theme: {self.theme}"})

        if self.language not in UserLanguage.values:
            raise ValidationError({"language": f"Invalid language: {self.language}"})

    def save(self, *args, **kwargs):
        self.full_clean()  # Run validation before saving
        super().save(*args, **kwargs)
