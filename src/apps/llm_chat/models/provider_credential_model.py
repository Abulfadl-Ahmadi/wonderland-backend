import uuid
from django.conf import settings
from django.db import models

from utils import EncryptedTextField
from .provider_model import LLMProvider


class UserProviderCredential(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="provider_credentials",
    )
    provider = models.ForeignKey(
        LLMProvider,
        on_delete=models.CASCADE,
        related_name="user_credentials",
    )
    label = models.CharField(max_length=100)
    secret = EncryptedTextField()
    is_active = models.BooleanField(default=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "User Provider Credential"
        verbose_name_plural = "User Provider Credentials"
        ordering = ("-updated_at",)
        constraints = [
            models.UniqueConstraint(
                fields=["user", "provider", "label"],
                name="llm_chat_user_provider_label_uniq",
            )
        ]

    def __str__(self) -> str:
        return f"{self.user_id} - {self.provider.slug} - {self.label}"
