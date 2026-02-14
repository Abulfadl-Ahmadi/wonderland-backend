import uuid
from django.db import models

from .provider_model import LLMProvider


class LLMModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    provider = models.ForeignKey(
        LLMProvider, on_delete=models.PROTECT, related_name="models"
    )
    name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=120, unique=True)
    is_active = models.BooleanField(default=True)
    context_window = models.IntegerField(null=True, blank=True)
    input_cost_per_1k = models.DecimalField(
        max_digits=12, decimal_places=6, null=True, blank=True
    )
    output_cost_per_1k = models.DecimalField(
        max_digits=12, decimal_places=6, null=True, blank=True
    )
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name = "LLM Model"
        verbose_name_plural = "LLM Models"
        ordering = ("provider", "name")

    def __str__(self) -> str:
        return f"{self.provider.name} - {self.name}"
