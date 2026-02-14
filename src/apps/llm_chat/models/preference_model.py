import uuid
from django.conf import settings
from django.db import models

from .llm_model import LLMModel
from .provider_credential_model import UserProviderCredential


class UserLLMPreference(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="llm_preference",
    )
    default_model = models.ForeignKey(
        LLMModel,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="user_preferences",
    )
    default_credential = models.ForeignKey(
        UserProviderCredential,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="preferences",
    )
    temperature = models.DecimalField(max_digits=4, decimal_places=3, null=True, blank=True)
    top_p = models.DecimalField(max_digits=4, decimal_places=3, null=True, blank=True)
    max_tokens = models.IntegerField(null=True, blank=True)
    system_prompt = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "User LLM Preference"
        verbose_name_plural = "User LLM Preferences"
        ordering = ("-updated_at",)

    def __str__(self) -> str:
        return f"{self.user_id} preferences"
