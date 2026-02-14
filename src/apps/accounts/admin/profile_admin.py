from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html

from apps.accounts.models import Profile


# Inline for Profile (editable inside User admin)
class ProfileInline(admin.StackedInline):
    extra = 0
    model = Profile
    can_delete = False
    verbose_name_plural = "Profile"
    readonly_fields = ("created_at", "updated_at", "id")
    fields = (
        "id",
        "first_name",
        "last_name",
        "national_code",
        "created_at",
        "updated_at",
    )

    def get_queryset(self, request):
        """Optimize queryset"""
        return super().get_queryset(request).select_related("user")


# Standalone admin for Profile
@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = [
        "user_phone",
        "full_name",
        "national_code",
        "created_at_pretty",
        "updated_at_pretty",
    ]
    list_filter = [
        "user__status",
        "user__role",
        "created_at",
    ]
    search_fields = [
        "user__phone_number",
        "first_name",
        "last_name",
        "national_code",
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
                    "first_name",
                    "last_name",
                )
            },
        ),
        (
            "Personal Info",
            {
                "fields": ("national_code",),
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
    def user_phone(self, obj: Profile) -> str:
        return format_html("<code>{}</code>", obj.user.phone_number)  # type: ignore

    @admin.display(description="Full Name")
    def full_name(self, obj: Profile) -> str:
        name = f"{obj.first_name} {obj.last_name}".strip()
        return name if name else "—"

    @admin.display(description="Created", ordering="created_at")
    def created_at_pretty(self, obj: Profile) -> str:
        return timezone.localtime(obj.created_at).strftime("%Y-%m-%d %H:%M")

    @admin.display(description="Updated", ordering="updated_at")
    def updated_at_pretty(self, obj: Profile) -> str:
        return timezone.localtime(obj.updated_at).strftime("%Y-%m-%d %H:%M")
