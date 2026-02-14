from rest_framework.exceptions import ValidationError
from django.contrib.auth.hashers import check_password
from rest_framework_simplejwt.tokens import RefreshToken

from constants import UserRole
from utils import normalize_iran_mobile
from apps.accounts.models import UserModel
from .user_service import UserService
from selectors_layer import UserSelectors
from repositories import UserRepository


class AuthService:
    """
    Service layer for authentication logic.
    Handles:
    - Register user
    - Login user
    - Token generation
    """

    @staticmethod
    def register(
        first_name: str,
        last_name: str,
        national_code: str,
        phone_number: str,
        password: str,
        confirm_password: str,
    ) -> UserModel:
        """
        Finalize user registration after OTP verification.

        Args:
            phone_number (str): User phone number.
            **extra_fields: Additional fields for user creation.

        Returns:
            UserModel: Newly created user.
        """

        # Normalize phone number
        normalized_phone_number = normalize_iran_mobile(phone_number)

        # Create new user via user service
        user = UserService.create_user(
            phone_number=normalized_phone_number,
            role=UserRole.USER,
            first_name=first_name,
            last_name=last_name,
            national_code=national_code,
            password=password,
        )

        return user

    @staticmethod
    def login(phone_number: str, password: str) -> tuple:
        """
        Login user with password and return JWT tokens.

        Args:
            phone_number (str): User phone number.
            password (str): Raw password.

        Returns:
            tuple: user instance + access + refresh token.

        Raises:
            ValidationError: If credentials are invalid or account inactive.
        """
        # Try to get user by phone number
        user = UserRepository.get_user_by_phone_number(phone_number)
        if not user:
            raise ValidationError(
                {"form": "Invalid credentials"}, code="invalid_credentials"
            )
        # Check if password is correct
        is_correct = check_password(password, user.password)
        if not is_correct:
            raise ValidationError(
                {"form": "Invalid credentials"}, code="invalid_credentials"
            )
        # Check if user is active
        is_active = UserSelectors.is_active(user)
        if not is_active:
            raise ValidationError(
                {"form": "Your account is inactive."}, code="inactive"
            )
        # Generate JWT tokens
        token = AuthService.generate_jwt_token(user)
        refresh_token = str(token)
        access_token = str(token.access_token)
        # Update last login time
        UserRepository.update_last_login(user)

        return user, access_token, refresh_token

    @staticmethod
    def generate_jwt_token(user: UserModel) -> RefreshToken:
        """
        Generate JWT tokens (access and refresh) and include additional data
        """
        token = RefreshToken.for_user(user)

        # Add custom claims to the token
        token["useId"] = str(user.id)
        token["role"] = user.role

        return token
