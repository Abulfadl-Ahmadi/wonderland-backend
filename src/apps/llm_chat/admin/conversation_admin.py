from django.contrib import admin

from apps.llm_chat.models import Conversation


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = [
        "user",
        "title",
        "is_archived",
        "updated_at",
    ]
    list_filter = [
        "is_archived",
    ]
    search_fields = [
        "title",
        "user__phone_number",
    ]
    ordering = [
        "-updated_at",
    ]
    list_per_page = 25
    save_on_top = True
