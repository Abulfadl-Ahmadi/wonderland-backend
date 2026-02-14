class DomainError(Exception):
    """Base domain exception."""


class OpenRouterConfigError(DomainError):
    """OpenRouter configuration error."""


class OpenRouterError(DomainError):
    """OpenRouter request error."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        error_code: str | None = None,
        raw: dict | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.error_code = error_code
        self.raw = raw or {}
