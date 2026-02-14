import os
from typing import Any

from django.db import models
from cryptography.fernet import Fernet


class EncryptedTextField(models.TextField):
    """
    TextField that encrypts values at rest using Fernet.

    The env var CREDENTIALS_ENCRYPTION_KEY must be set to a valid Fernet key.
    """

    prefix = "enc::"
    _fernet_instance: Fernet | None = None

    def get_prep_value(self, value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, str) and value.startswith(self.prefix):
            return value
        fernet = self._get_fernet()
        token = fernet.encrypt(str(value).encode("utf-8")).decode("utf-8")
        return f"{self.prefix}{token}"

    def from_db_value(self, value: Any, expression, connection) -> Any:
        return self.to_python(value)

    def to_python(self, value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, str) and value.startswith(self.prefix):
            token = value[len(self.prefix) :]
            try:
                return self._get_fernet().decrypt(token.encode("utf-8")).decode("utf-8")
            except Exception:
                # Avoid leaking encrypted contents if decrypt fails.
                return ""
        return value

    @classmethod
    def _get_fernet(cls) -> Fernet:
        if cls._fernet_instance is not None:
            return cls._fernet_instance
        key = os.getenv("CREDENTIALS_ENCRYPTION_KEY", "").strip()
        if not key:
            raise ValueError("CREDENTIALS_ENCRYPTION_KEY is not configured.")
        cls._fernet_instance = Fernet(key)
        return cls._fernet_instance
