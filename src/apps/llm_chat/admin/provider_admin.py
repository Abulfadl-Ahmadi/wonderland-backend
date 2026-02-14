from django.contrib import admin

from apps.llm_chat.models import LLMProvider


@admin.register(LLMProvider)
class LLMProviderAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "slug",
        "is_active",
        "created_at",
        "updated_at",
    ]
    list_filter = [
        "is_active",
    ]
    search_fields = [
        "name",
        "slug",
    ]
    ordering = [
        "name",
    ]
    list_per_page = 25
    save_on_top = True
