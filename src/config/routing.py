from django.urls import re_path

from apps.llm_chat.ws.consumers import ChatConsumer

# WebSocket URL routing
websocket_urlpatterns = [
    re_path(r"^ws/chat/$", ChatConsumer.as_asgi()),
]
