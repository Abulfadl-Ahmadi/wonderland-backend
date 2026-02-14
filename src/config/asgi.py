import os

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter

from config.routing import websocket_urlpatterns
from apps.authentication.ws.jwt_auth import JwtAuthMiddlewareStack

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

django_asgi_app = get_asgi_application()

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": JwtAuthMiddlewareStack(
            get_websocket_application(),
        ),
    }
)


def get_websocket_application():
    from channels.routing import URLRouter
    return URLRouter(websocket_urlpatterns)
