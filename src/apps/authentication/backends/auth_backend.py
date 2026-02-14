from utils import normalize_iran_mobile

from django.http import HttpRequest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.contrib.auth.backends import ModelBackend


class AuthIranPhoneBackend(ModelBackend):
    """
    Authenticate users using Iranian mobile numbers in any input format.
    Stores phone numbers normalized as +989xxxxxxxxx, and normalizes input before lookup.
    """

    def authenticate(
        self,
        request: HttpRequest,
        username=None,
        password=None,
        phone_number=None,
        **kwargs,
    ):
        User = get_user_model()

        # Django typically passes "username"
        raw = phone_number or username or kwargs.get(User.USERNAME_FIELD)

        if not raw or password is None:
            return None

        try:
            normalized = normalize_iran_mobile(raw)
        except ValidationError:
            return None

        try:
            user = User.objects.get(phone_number=normalized)
        except User.DoesNotExist:
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user

        return None
