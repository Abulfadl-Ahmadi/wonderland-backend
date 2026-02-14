from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html

from apps.accounts.models import Settings
from constants import UserTheme, UserLanguage


# Inline for Settings (editable inside User admin)
class SettingsInline(admin.StackedInline):
    extra = 0
    model = Settings
    can_delete = False
    verbose_name_plural = "Settings"
    readonly_fields = ("id", "created_at", "updated_at")
    fieldsets = (
        ("Appearance", {"fields": ("theme", "language")}),
        ("Timestamps", {"fields": ("id", "created_at", "updated_at")}),
    )

    def get_queryset(self, request):
        """Optimize queryset"""
        return super().get_queryset(request).select_related("user")


# Standalone admin for Settings
@admin.register(Settings)
class SettingsAdmin(admin.ModelAdmin):
    list_display = [
        "user_phone",
        "theme_badge",
        "language_badge",
        "created_at_pretty",
        "updated_at_pretty",
    ]
    list_filter = [
        "theme",
        "language",
        "created_at",
    ]
    search_fields = [
        "user__phone_number",
    ]
    readonly_fields = [
        "id",
        "created_at",
        "updated_at",
    ]
    ordering = [
        "-created_at",
    ]
    date_hierarchy = "created_at"
    list_per_page = 25
    save_on_top = True

    fieldsets = (
        (
            "Basic Info",
            {
                "fields": (
                    "id",
                    "user",
                )
            },
        ),
        (
            "Appearance",
            {
                "fields": (
                    "theme",
                    "language",
                ),
            },
        ),
        (
            "Important dates",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )

    @admin.display(description="User Phone", ordering="user__phone_number")
    def user_phone(self, obj: Settings) -> str:
        return format_html("<code>{}</code>", obj.user.phone_number)  # type: ignore

    @admin.display(description="Theme", ordering="theme")
    def theme_badge(self, obj: Settings) -> str:
        colors = {
            UserTheme.LIGHT.value: "#fbbf24",  # amber
            UserTheme.DARK.value: "#1f2937",  # gray-800
            UserTheme.SYSTEM.value: "#06b6d4",  # cyan
        }
        color = colors.get(obj.theme, "#6b7280")

        label = (
            UserTheme(obj.theme).label if obj.theme in UserTheme.values else obj.theme
        )

        return format_html(
            '<span style="padding:2px 8px;border-radius:999px;'
            'background:{}22;color:{};font-weight:600;">{}</span>',
            color,
            color,
            label,
        )

    @admin.display(description="Language", ordering="language")
    def language_badge(self, obj: Settings) -> str:
        colors = {
            UserLanguage.ENGLISH.value: "#3b82f6",  # blue
            UserLanguage.PERSIAN.value: "#e11d48",  # rose
        }
        color = colors.get(obj.language, "#6b7280")

        label = (
            UserLanguage(obj.language).label
            if obj.language in UserLanguage.values
            else obj.language
        )

        return format_html(
            '<span style="padding:2px 8px;border-radius:999px;'
            'background:{}22;color:{};font-weight:600;">{}</span>',
            color,
            color,
            label,
        )

    @admin.display(description="Created", ordering="created_at")
    def created_at_pretty(self, obj: Settings) -> str:
        return timezone.localtime(obj.created_at).strftime("%Y-%m-%d %H:%M")

    @admin.display(description="Updated", ordering="updated_at")
    def updated_at_pretty(self, obj: Settings) -> str:
        return timezone.localtime(obj.updated_at).strftime("%Y-%m-%d %H:%M")
