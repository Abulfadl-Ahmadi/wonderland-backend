"""
LLM Service - Transport-agnostic interface for streaming LLM completions.

This service wraps provider-specific implementations (OpenRouter, etc.) and provides
a clean contract for transport layers (WebSocket, SSE, HTTP) to consume.

Design:
- stream_completion(): Generator yielding normalized chunks
- Metadata collected during streaming, yielded at end
- Consumer decides persistence, formatting, and transport
"""

from typing import Any, Generator, Mapping, Optional

from services.openrouter_service import OpenRouterService


class LLMService:
    """
    Transport-agnostic LLM streaming service.
    
    Provides a unified interface for different LLM providers.
    """

    @staticmethod
    def stream_completion(
        model_slug: str,
        messages: list[dict[str, Any]],
        provider: str = "openrouter",
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> Generator[dict[str, Any], None, None]:
        """
        Stream LLM response in a transport-agnostic format.
        
        Args:
            model_slug: Model identifier (e.g., "gpt-4-turbo").
            messages: Conversation history as [{role, content}, ...].
            provider: LLM provider ("openrouter" is default/only option currently).
            temperature: LLM temperature (0-2).
            top_p: LLM top_p (0-1).
            max_tokens: Max completion tokens.
        
        Yields:
            Delta chunks:
            {
                "type": "delta",
                "delta": "token text",
                "raw_chunk": {...}  # Provider-specific chunk
            }
            
            Done chunk (after all deltas):
            {
                "type": "done",
                "delta": "",
                "usage": {
                    "prompt_tokens": int,
                    "completion_tokens": int,
                    "total_tokens": int
                },
                "raw_response": {...}  # Provider-specific final response
            }
            
            Error chunk (on failure):
            {
                "type": "error",
                "error_code": str,
                "error_message": str,
                "raw": {...}  # Provider-specific error payload
            }
        """
        if provider == "openrouter":
            yield from LLMService._stream_openrouter(
                model_slug=model_slug,
                messages=messages,
                temperature=temperature,
                top_p=top_p,
                max_tokens=max_tokens,
            )
        else:
            yield {
                "type": "error",
                "error_code": "unsupported_provider",
                "error_message": f"LLM provider '{provider}' not supported. Use 'openrouter'.",
                "raw": {},
            }

    @staticmethod
    def _stream_openrouter(
        model_slug: str,
        messages: list[dict[str, Any]],
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> Generator[dict[str, Any], None, None]:
        """
        Delegate to OpenRouterService streaming.
        """
        yield from OpenRouterService.stream_chat_completion(
            model_slug=model_slug,
            messages=messages,
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
        )

    @staticmethod
    def get_model_info(model_slug: str, provider: str = "openrouter") -> Optional[dict[str, Any]]:
        """
        Get information about a model (for future use).
        Returns model metadata like context window, pricing, capabilities.
        """
        # TODO: Implement when we have model registry
        return None
