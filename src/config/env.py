import os
from dotenv import load_dotenv


load_dotenv()


WONDERLAND_STAGE = os.getenv("WONDERLAND_STAGE", "development")


def _is_test_environment() -> bool:
    settings_module = os.getenv("DJANGO_SETTINGS_MODULE", "")
    return settings_module.endswith(".test") or settings_module.endswith(".tests")


ENV_SECRET_KEY: str | None = os.getenv("SECRET_KEY")
if not ENV_SECRET_KEY and not _is_test_environment():
    raise RuntimeError("SECRET_KEY must be set in non-test environments.")

ENV_BASE_URL: str = os.getenv("BASE_URL", "api/")
ENV_ADMIN_URL: str = os.getenv("ADMIN_URL", "admin/")

ENV_REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/1")
ENV_LLM_CHAT_MAX_MESSAGE_LENGTH: int = int(os.getenv("LLM_CHAT_MAX_MESSAGE_LENGTH", 4000))


# ---------------------------------------------------------------
# Email Configuration
# ---------------------------------------------------------------
ENV_EMAIL_BACKEND: str = os.getenv(
    "EMAIL_BACKEND", "django.core.mail.backends.smtp.EmailBackend"
)
ENV_EMAIL_HOST: str | None = os.getenv("EMAIL_HOST")
ENV_EMAIL_PORT: int = int(os.getenv("EMAIL_PORT", 587))
ENV_EMAIL_USE_TLS: bool = os.getenv("EMAIL_USE_TLS", "True") == "True"
ENV_EMAIL_HOST_USER: str | None = os.getenv("EMAIL_HOST_USER")
ENV_EMAIL_HOST_PASSWORD: str | None = os.getenv("EMAIL_HOST_PASSWORD")
ENV_DEFAULT_FROM_EMAIL: str | None = os.getenv("DEFAULT_FROM_EMAIL")
ENV_MAX_RETRY_ATTEMPTS: int = int(os.getenv("MAX_RETRY_ATTEMPTS", 3))

# ---------------------------------------------------------------
# JWT & AUTH Configuration
# ---------------------------------------------------------------
ENV_OTP_LENGTH: int = int(os.getenv("OTP_LENGTH", 6))
ENV_OTP_EXPIRY_MINUTES: int = int(os.getenv("OTP_EXPIRY_MINUTES", 5))
ENV_MAX_VERIFY_ATTEMPTS: int = int(os.getenv("MAX_VERIFY_ATTEMPTS", 3))

ENV_MINUTES: int = int(os.getenv("ACCESS_TOKEN_LIFETIME", 15))
ENV_HOURS: int = int(os.getenv("REFRESH_TOKEN_LIFETIME", 24))