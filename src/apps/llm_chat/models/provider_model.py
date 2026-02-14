import uuid
from django.db import models


class ProviderAuthType(models.TextChoices):
    API_KEY = "api_key", "API Key"


class LLMProvider(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True)
    base_url = models.URLField(blank=True, null=True)
    auth_type = models.CharField(
        max_length=20,
        choices=ProviderAuthType.choices,
        default=ProviderAuthType.API_KEY,
    )
    supports_openai_compatible = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "LLM Provider"
        verbose_name_plural = "LLM Providers"
        ordering = ("name",)

    def __str__(self) -> str:
        return self.name
