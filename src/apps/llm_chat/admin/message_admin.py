from django.contrib import admin

from apps.llm_chat.models import Message


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = [
        "conversation",
        "role",
        "created_at",
        "model_used",
        "total_tokens",
        "total_cost",
    ]
    list_filter = [
        "role",
        "model_used",
    ]
    search_fields = [
        "content",
    ]
    ordering = [
        "created_at",
    ]
    list_per_page = 25
    save_on_top = True
