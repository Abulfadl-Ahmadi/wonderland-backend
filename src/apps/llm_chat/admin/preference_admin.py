from django.contrib import admin

from apps.llm_chat.models import UserLLMPreference


@admin.register(UserLLMPreference)
class UserLLMPreferenceAdmin(admin.ModelAdmin):
    list_display = [
        "user",
        "default_model",
        "updated_at",
    ]
    ordering = [
        "-updated_at",
    ]
    list_per_page = 25
    save_on_top = True
