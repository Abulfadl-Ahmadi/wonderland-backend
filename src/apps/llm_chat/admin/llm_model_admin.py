from django.contrib import admin

from apps.llm_chat.models import LLMModel


@admin.register(LLMModel)
class LLMModelAdmin(admin.ModelAdmin):
    list_display = [
        "provider",
        "name",
        "slug",
        "is_active",
    ]
    list_filter = [
        "provider",
        "is_active",
    ]
    search_fields = [
        "name",
        "slug",
    ]
    ordering = [
        "provider",
        "name",
    ]
    list_per_page = 25
    save_on_top = True
