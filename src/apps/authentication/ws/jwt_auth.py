from __future__ import annotations

from urllib.parse import parse_qs
from typing import Optional

from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import TokenError


class JwtAuthMiddleware:
    """
    Channels middleware that authenticates WebSocket connections using JWT.

    Accepts token via:
    - query string: ?token=<jwt>
    - header: Authorization: Bearer <jwt>

    If token is invalid, scope["jwt_invalid"] is set to True.
    """

    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        token = self._get_token(scope)

        if token:
            try:
                validated = AccessToken(token)
                user = await self._get_user(validated)
                scope["user"] = user or AnonymousUser()
                scope["jwt_invalid"] = user is None
            except TokenError:
                scope["user"] = AnonymousUser()
                scope["jwt_invalid"] = True
        else:
            scope["jwt_invalid"] = False

        return await self.inner(scope, receive, send)

    @staticmethod
    def _get_token(scope) -> Optional[str]:
        query_string = scope.get("query_string", b"").decode("utf-8")
        if query_string:
            params = parse_qs(query_string)
            token_list = params.get("token")
            if token_list:
                return token_list[0]

        headers = dict(scope.get("headers") or [])
        auth_header = headers.get(b"authorization")
        if not auth_header:
            return None
        try:
            value = auth_header.decode("utf-8")
        except Exception:
            return None
        if not value.lower().startswith("bearer "):
            return None
        return value.split(" ", 1)[1].strip()

    @staticmethod
    @database_sync_to_async
    def _get_user(token: AccessToken):
        user_id = token.get("user_id")
        if not user_id:
            return None
        User = get_user_model()
        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            return None


def JwtAuthMiddlewareStack(inner):
    from channels.auth import AuthMiddlewareStack

    return JwtAuthMiddleware(AuthMiddlewareStack(inner))
