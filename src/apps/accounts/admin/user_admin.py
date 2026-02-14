from django.contrib import admin
from django.utils import timezone
from django.http import HttpRequest
from django.db.models import QuerySet
from django.utils.html import format_html
from django.core.exceptions import ValidationError
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from utils import normalize_iran_mobile
from apps.accounts.models import UserModel
from constants import UserRole, UserStatus
from .profile_admin import ProfileInline
from .settings_admin import SettingsInline


@admin.register(UserModel)
class UserAdmin(BaseUserAdmin):
    """Admin configuration for UserModel"""

    list_per_page = 25
    save_on_top = True
    date_hierarchy = "created_at"

    inlines = [ProfileInline, SettingsInline]

    list_display = (
        "phone_number_pretty",
        "status_badge",
        "role_badge",
        # "staff_badge",
        # "superuser_badge",
        "last_login_pretty",
        "updated_at_pretty",
        "created_at_pretty",
    )
    list_display_links = ("phone_number_pretty",)

    search_fields = ("phone_number",)
    search_help_text = (
        "Search by phone: +989..., 09..., 9... (Persian digits supported)."
    )

    list_filter = ("role", "status", "groups", "is_superuser")
    ordering = ("-created_at",)

    readonly_fields = (
        "id",
        "last_login",
        "updated_at",
        "created_at",
        "is_active",
        "is_staff",
        "is_superuser",
    )

    actions = (
        "mark_active",
        "mark_inactive",
        "ban_users",
        "unban_users",
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "phone_number",
                    "role",
                    "status",
                    "password1",
                    "password2",
                ),
            },
        ),
    )

    fieldsets = (
        ("Basic Info", {"fields": ("id", "phone_number", "password")}),
        (
            "Role & Status",
            {"fields": ("role", "status", "is_active", "is_staff", "is_superuser")},
        ),
        (
            "Permissions",
            {"classes": ("collapse",), "fields": ("groups", "user_permissions")},
        ),
        ("Important Dates", {"fields": ("last_login", "created_at", "updated_at")}),
    )

    # ---------------------------------------------------------------------
    # Pretty columns
    # ---------------------------------------------------------------------

    @admin.display(description="Phone", ordering="phone_number")
    def phone_number_pretty(self, obj: UserModel) -> str:
        return format_html("<code>{}</code>", obj.phone_number)

    @admin.display(description="Status", ordering="status")
    def status_badge(self, obj: UserModel) -> str:
        colors: dict[str, str] = {
            UserStatus.ACTIVE.value: "#16a34a",  # green
            UserStatus.INACTIVE.value: "#f59e0b",  # amber
            UserStatus.BANNED.value: "#dc2626",  # red
        }
        color = colors.get(obj.status, "#6b7280")  # gray fallback

        # Pylance-friendly label resolution
        label = (
            UserStatus(obj.status).label
            if obj.status in UserStatus.values
            else obj.status
        )

        return format_html(
            '<span style="padding:2px 8px;border-radius:999px;'
            'background:{}22;color:{};font-weight:600;">{}</span>',
            color,
            color,
            label,
        )

    @admin.display(description="Role", ordering="role")
    def role_badge(self, obj: UserModel) -> str:
        colors: dict[str, str] = {
            UserRole.USER.value: "#2563eb",  # blue
            UserRole.ADMIN.value: "#7c3aed",  # purple
            # UserRole.SUPERUSER.value: "#111827",  # near black
            UserRole.SUPERUSER.value: "#16a34a",  # green
        }
        color = colors.get(obj.role, "#6b7280")

        label = UserRole(obj.role).label if obj.role in UserRole.values else obj.role

        return format_html(
            '<span style="padding:2px 8px;border-radius:999px;'
            'background:{}22;color:{};font-weight:600;">{}</span>',
            color,
            color,
            label,
        )

    @admin.display(description="Staff", boolean=True)
    def staff_badge(self, obj: UserModel) -> bool:
        return bool(obj.is_staff)

    @admin.display(description="SU", boolean=True)
    def superuser_badge(self, obj: UserModel) -> bool:
        return bool(obj.is_superuser)

    @admin.display(description="Last login", ordering="last_login")
    def last_login_pretty(self, obj: UserModel) -> str:
        if not obj.last_login:
            return "—"
        return timezone.localtime(obj.last_login).strftime("%Y-%m-%d %H:%M")

    @admin.display(description="Updated", ordering="updated_at")
    def updated_at_pretty(self, obj: UserModel) -> str:
        return timezone.localtime(obj.updated_at).strftime("%Y-%m-%d %H:%M")

    @admin.display(description="Created", ordering="created_at")
    def created_at_pretty(self, obj: UserModel) -> str:
        return timezone.localtime(obj.created_at).strftime("%Y-%m-%d %H:%M")

    # ---------------------------------------------------------------------
    # Actions (safe: won't affect superusers)
    # ---------------------------------------------------------------------

    def _exclude_superusers(self, queryset: QuerySet[UserModel]) -> QuerySet[UserModel]:
        return queryset.exclude(is_superuser=True)

    @admin.action(description="Mark selected users as ACTIVE")
    def mark_active(self, request: HttpRequest, queryset: QuerySet[UserModel]):
        updated = self._exclude_superusers(queryset).update(status=UserStatus.ACTIVE)
        self.message_user(
            request, f"{updated} user(s) marked as ACTIVE. (Superusers unchanged)"
        )

    @admin.action(description="Mark selected users as INACTIVE")
    def mark_inactive(self, request: HttpRequest, queryset: QuerySet[UserModel]):
        updated = self._exclude_superusers(queryset).update(status=UserStatus.INACTIVE)
        self.message_user(
            request, f"{updated} user(s) marked as INACTIVE. (Superusers unchanged)"
        )

    @admin.action(description="Ban selected users")
    def ban_users(self, request: HttpRequest, queryset: QuerySet[UserModel]):
        updated = self._exclude_superusers(queryset).update(status=UserStatus.BANNED)
        self.message_user(request, f"{updated} user(s) banned. (Superusers unchanged)")

    @admin.action(description="Unban selected users (set ACTIVE)")
    def unban_users(self, request: HttpRequest, queryset: QuerySet[UserModel]):
        updated = self._exclude_superusers(queryset).update(status=UserStatus.ACTIVE)
        self.message_user(
            request, f"{updated} user(s) unbanned (ACTIVE). (Superusers unchanged)"
        )

    # ---------------------------------------------------------------------
    # Search normalization
    # ---------------------------------------------------------------------

    def get_search_results(self, request, queryset, search_term):
        qs, use_distinct = super().get_search_results(request, queryset, search_term)

        if search_term:
            try:
                normalized = normalize_iran_mobile(search_term)
            except ValidationError:
                return qs, use_distinct

            qs |= self.model.objects.filter(phone_number=normalized)

        return qs, use_distinct
