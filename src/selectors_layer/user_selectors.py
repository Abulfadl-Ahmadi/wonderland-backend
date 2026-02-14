from constants import UserStatus, UserRole
from apps.accounts.models import UserModel


class UserSelectors:
    """
    Selector class for UserModel.
    Contains read-only methods to check user properties.
    """

    @staticmethod
    def is_active(user: UserModel) -> bool:
        """
        Check if the user is active.

        Args:
            user (UserModel): User instance.

        Returns:
            bool: True if user status is ACTIVE.
        """
        return user.status == UserStatus.ACTIVE

    @staticmethod
    def is_admin(user: UserModel) -> bool:
        """
        Check if the user has admin privileges.

        Args:
            user (UserModel): User instance.

        Returns:
            bool: True if user role is ADMIN and is_staff is True.
        """
        return user.role == UserRole.ADMIN and user.is_staff

    @staticmethod
    def is_superuser(user: UserModel) -> bool:
        """
        Check if the user is a superuser.

        Args:
            user (UserModel): User instance.

        Returns:
            bool: True if user role is SUPERUSER, is_superuser and is_staff are True.
        """
        return user.role == UserRole.SUPERUSER and user.is_superuser and user.is_staff
