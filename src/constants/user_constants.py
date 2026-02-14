from django.db import models


MAX_AVATAR_SIZE_MB = 2
MAX_AVATAR_SIZE = 2 * 1024 * 1024
VALID_AVATAR_EXTENSIONS = [".jpg", ".jpeg", ".png", ".webp"]


class UserStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    BANNED = "banned", "Banned"
    INACTIVE = "inactive", "Inactive"


class UserRole(models.TextChoices):
    USER = "user", "User"
    ADMIN = "admin", "Admin"
    SUPERUSER = "superuser", "Superuser"


class UserTheme(models.TextChoices):
    LIGHT = "light", "Light"
    DARK = "dark", "Dark"
    SYSTEM = "system", "System"


class UserLanguage(models.TextChoices):
    ENGLISH = "en", "English"
    PERSIAN = "fa", "Persian"