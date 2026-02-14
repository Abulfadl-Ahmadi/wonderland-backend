import uuid
from django.db import models

from .conversation_model import Conversation
from .llm_model import LLMModel
from .provider_credential_model import UserProviderCredential


class MessageRole(models.TextChoices):
    SYSTEM = "system", "System"
    USER = "user", "User"
    ASSISTANT = "assistant", "Assistant"
    TOOL = "tool", "Tool"


class MessageStatus(models.TextChoices):
    """Status of a message during its lifecycle."""
    STREAMING = "streaming", "Streaming (in progress)"
    COMPLETED = "completed", "Completed"
    ERROR = "error", "Error"


class Message(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name="messages"
    )
    role = models.CharField(max_length=20, choices=MessageRole.choices)
    status = models.CharField(
        max_length=20,
        choices=MessageStatus.choices,
        default=MessageStatus.COMPLETED,
        help_text="Message status: streaming (in progress), completed, or error."
    )
    content = models.TextField()
    model_used = models.ForeignKey(
        LLMModel, on_delete=models.SET_NULL, null=True, blank=True, related_name="messages"
    )
    credential_used = models.ForeignKey(
        UserProviderCredential,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="messages",
    )
    raw_response = models.JSONField(null=True, blank=True)
    error_code = models.CharField(max_length=100, null=True, blank=True)
    error_message = models.TextField(null=True, blank=True)
    prompt_tokens = models.IntegerField(null=True, blank=True)
    completion_tokens = models.IntegerField(null=True, blank=True)
    total_tokens = models.IntegerField(null=True, blank=True)
    input_cost = models.DecimalField(max_digits=12, decimal_places=6, null=True, blank=True)
    output_cost = models.DecimalField(max_digits=12, decimal_places=6, null=True, blank=True)
    total_cost = models.DecimalField(max_digits=12, decimal_places=6, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, help_text="Last update time for streaming status/completion tracking.")

    class Meta:
        verbose_name = "Message"
        verbose_name_plural = "Messages"
        ordering = ("created_at",)
        indexes = [
            models.Index(
                fields=["conversation", "created_at"],
                name="llm_chat_msg_conv_created_idx",
            ),
            models.Index(fields=["role"], name="llm_chat_msg_role_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.role} message"
