from django.urls import path

from .views import (
	LLMModelListAPIView,
	ConversationListCreateAPIView,
	ConversationDetailAPIView,
	MessageListCreateAPIView,
	UserLLMPreferenceAPIView,
)


urlpatterns = [
	path("models/", LLMModelListAPIView.as_view(), name="llm-models"),
	path("conversations/", ConversationListCreateAPIView.as_view(), name="conversations"),
	path(
		"conversations/<uuid:conversation_id>/",
		ConversationDetailAPIView.as_view(),
		name="conversation-detail",
	),
	path(
		"conversations/<uuid:conversation_id>/messages/",
		MessageListCreateAPIView.as_view(),
		name="conversation-messages",
	),
	path("preferences/", UserLLMPreferenceAPIView.as_view(), name="preferences"),
]
