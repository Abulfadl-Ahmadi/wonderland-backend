from typing import Any, AsyncGenerator, Optional

from apps.llm_chat.models import LLMModel
from services.llm_service import LLMService


class ChatStreamService:
    """
    Service layer for LLM streaming orchestration.
    """

    @staticmethod
    async def stream_response(
        model: LLMModel,
        messages: list[dict[str, Any]],
        api_key: Optional[str] = None,
    ) -> AsyncGenerator[dict[str, Any], None]:
        base_url = model.provider.base_url or None
        async for chunk in LLMService.stream_completion_async(
            model_slug=model.slug,
            messages=messages,
            api_key=api_key,
            base_url=base_url,
        ):
            yield chunk
