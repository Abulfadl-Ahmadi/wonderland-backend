import uuid
from django.db import models
from django.contrib.auth import get_user_model


UserModel = get_user_model()


class Profile(models.Model):
    """Extended user profile with avatar support and validations."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        UserModel, on_delete=models.CASCADE, related_name="profile", db_index=True
    )

    national_code = models.CharField(max_length=10, blank=True, db_index=True)

    last_name = models.CharField(max_length=150, blank=True, null=True)
    first_name = models.CharField(max_length=150, blank=True, null=True)

    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"

    def __str__(self) -> str:
        return f"{self.full_name}'s profile"

    @property
    def full_name(self) -> str:
        """Return the user's full name."""
        full_name = f"{self.first_name} {self.last_name}".strip()
        if not full_name:
            return self.user.phone_number  # type: ignore
        return full_name
