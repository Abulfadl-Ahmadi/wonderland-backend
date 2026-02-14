import json
import os
import threading
import itertools
from typing import Any, Mapping, Optional, AsyncGenerator
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import httpx

from common.exceptions import OpenRouterConfigError, OpenRouterError


class OpenRouterService:
    """
    Service for interacting with OpenRouter APIs.
    """

    _lock = threading.Lock()
    _counter = itertools.count(0)

    @staticmethod
    def chat_completion(
        model_slug: str,
        messages: list[dict[str, Any]],
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        max_tokens: Optional[int] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ) -> dict[str, Any]:
        base_url, api_key = OpenRouterService._resolve_config(
            api_key=api_key,
            base_url=base_url,
        )

        payload: dict[str, Any] = {
            "model": model_slug,
            "messages": messages,
        }
        if temperature is not None:
            payload["temperature"] = temperature
        if top_p is not None:
            payload["top_p"] = top_p
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        url = base_url.rstrip("/") + "/chat/completions"
        request = Request(
            url=url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urlopen(request, timeout=30) as response:
                raw_bytes = response.read()
                raw_json = json.loads(raw_bytes.decode("utf-8"))
        except HTTPError as exc:
            raw_json = OpenRouterService._read_error_payload(exc)
            raise OpenRouterError(
                "OpenRouter request failed",
                status_code=exc.code,
                error_code=OpenRouterService._extract_error_code(raw_json),
                raw=raw_json,
            )
        except URLError as exc:
            raise OpenRouterError(
                "OpenRouter request failed",
                status_code=None,
                error_code="network_error",
                raw={"detail": str(exc)},
            )

        assistant_text = OpenRouterService._extract_assistant_text(raw_json)
        usage = OpenRouterService._extract_usage(raw_json)

        return {
            "assistant_text": assistant_text,
            "usage": usage,
            "raw": raw_json,
        }

    @staticmethod
    def stream_chat_completion(
        model_slug: str,
        messages: list[dict[str, Any]],
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        max_tokens: Optional[int] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        """
        Stream LLM response tokens from OpenRouter in a transport-agnostic way.
        
        Yields chunks:
          - Delta chunk: {"type": "delta", "delta": "text", "raw_chunk": {...}}
          - Done chunk:  {"type": "done", "delta": "...", "usage": {...}, "raw_response": {...}}
          - Error chunk: {"type": "error", "error_code": "...", "error_message": "...", "raw": {...}}
        
        This generator is transport-agnostic: the consumer (WebSocket, SSE, etc.)
        decides how to send each chunk. Message persistence is decoupled from streaming.
        """
        base_url, api_key = OpenRouterService._resolve_config(
            api_key=api_key,
            base_url=base_url,
        )

        payload: dict[str, Any] = {
            "model": model_slug,
            "messages": messages,
            "stream": True,
        }
        if temperature is not None:
            payload["temperature"] = temperature
        if top_p is not None:
            payload["top_p"] = top_p
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        url = base_url.rstrip("/") + "/chat/completions"
        request = Request(
            url=url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        final_response = None
        final_usage = None

        try:
            with urlopen(request, timeout=30) as response:
                for line in response:
                    line_str = line.decode("utf-8").strip()
                    if not line_str or line_str == "[DONE]":
                        continue
                    if line_str.startswith("data: "):
                        line_str = line_str[6:]
                    try:
                        chunk = json.loads(line_str)
                        # Track final response when usage data arrives
                        if chunk.get("usage"):
                            final_response = chunk
                            final_usage = chunk.get("usage")
                        # Yield delta chunk
                        delta = (chunk.get("choices") or [{}])[0].get("delta", {}).get("content", "")
                        yield {
                            "type": "delta",
                            "delta": delta or "",
                            "raw_chunk": chunk,
                        }
                    except json.JSONDecodeError:
                        continue
            
            # Yield final metadata chunk after stream completes
            if final_usage:
                yield {
                    "type": "done",
                    "delta": "",
                    "usage": {
                        "prompt_tokens": final_usage.get("prompt_tokens"),
                        "completion_tokens": final_usage.get("completion_tokens"),
                        "total_tokens": final_usage.get("total_tokens"),
                    },
                    "raw_response": final_response,
                }
            else:
                # Stream ended without usage data (shouldn't happen, but handle gracefully)
                yield {
                    "type": "done",
                    "delta": "",
                    "usage": {
                        "prompt_tokens": None,
                        "completion_tokens": None,
                        "total_tokens": None,
                    },
                    "raw_response": None,
                }

        except HTTPError as exc:
            raw_json = OpenRouterService._read_error_payload(exc)
            yield {
                "type": "error",
                "error_code": OpenRouterService._extract_error_code(raw_json) or "http_error",
                "error_message": f"OpenRouter HTTP {exc.code}",
                "raw": raw_json,
            }
        except URLError as exc:
            yield {
                "type": "error",
                "error_code": "network_error",
                "error_message": str(exc),
                "raw": {"detail": str(exc)},
            }

    @staticmethod
    async def stream_chat_completion_async(
        model_slug: str,
        messages: list[dict[str, Any]],
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        max_tokens: Optional[int] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """
        Async streaming for OpenRouter chat completions.

        Yields the same chunk contract as stream_chat_completion().
        """
        base_url, api_key = OpenRouterService._resolve_config(
            api_key=api_key,
            base_url=base_url,
        )

        payload: dict[str, Any] = {
            "model": model_slug,
            "messages": messages,
            "stream": True,
        }
        if temperature is not None:
            payload["temperature"] = temperature
        if top_p is not None:
            payload["top_p"] = top_p
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        url = base_url.rstrip("/") + "/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        final_response = None
        final_usage = None

        timeout = httpx.Timeout(30.0, read=30.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                async with client.stream("POST", url, json=payload, headers=headers) as response:
                    if response.status_code >= 400:
                        raw_json = await OpenRouterService._read_error_payload_async(response)
                        yield {
                            "type": "error",
                            "error_code": OpenRouterService._extract_error_code(raw_json) or "http_error",
                            "error_message": f"OpenRouter HTTP {response.status_code}",
                            "raw": raw_json,
                        }
                        return

                    async for line in response.aiter_lines():
                        line_str = line.strip()
                        if not line_str or line_str == "[DONE]":
                            continue
                        if line_str.startswith("data: "):
                            line_str = line_str[6:]
                        try:
                            chunk = json.loads(line_str)
                            if chunk.get("usage"):
                                final_response = chunk
                                final_usage = chunk.get("usage")
                            delta = (chunk.get("choices") or [{}])[0].get("delta", {}).get("content", "")
                            yield {
                                "type": "delta",
                                "delta": delta or "",
                                "raw_chunk": chunk,
                            }
                        except json.JSONDecodeError:
                            continue

                if final_usage:
                    yield {
                        "type": "done",
                        "delta": "",
                        "usage": {
                            "prompt_tokens": final_usage.get("prompt_tokens"),
                            "completion_tokens": final_usage.get("completion_tokens"),
                            "total_tokens": final_usage.get("total_tokens"),
                        },
                        "raw_response": final_response,
                    }
                else:
                    yield {
                        "type": "done",
                        "delta": "",
                        "usage": {
                            "prompt_tokens": None,
                            "completion_tokens": None,
                            "total_tokens": None,
                        },
                        "raw_response": None,
                    }
            except httpx.RequestError as exc:
                yield {
                    "type": "error",
                    "error_code": "network_error",
                    "error_message": str(exc),
                    "raw": {"detail": str(exc)},
                }

    # ------------------------------------------------------------------
    # INTERNAL HELPERS
    # ------------------------------------------------------------------

    @staticmethod
    def _get_openrouter_config() -> tuple[str, list[str]]:
        base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
        keys_raw = os.getenv("OPENROUTER_API_KEYS", "")
        api_keys = [key.strip() for key in keys_raw.split(",") if key.strip()]
        if not api_keys:
            raise OpenRouterConfigError("OPENROUTER_API_KEYS is not configured.")
        return base_url, api_keys

    @classmethod
    def _resolve_config(
        cls,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ) -> tuple[str, str]:
        if api_key:
            resolved_key = api_key
        else:
            cfg_base, api_keys = cls._get_openrouter_config()
            resolved_key = cls._select_api_key(api_keys)
            if not base_url:
                base_url = cfg_base
        resolved_base_url = base_url or os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
        return resolved_base_url, resolved_key

    @classmethod
    def _select_api_key(cls, api_keys: list[str]) -> str:
        if not api_keys:
            raise OpenRouterConfigError("OPENROUTER_API_KEYS is not configured.")
        with cls._lock:
            index = next(cls._counter) % len(api_keys)
        return api_keys[index]

    @staticmethod
    def _extract_assistant_text(raw_json: Mapping[str, Any]) -> str:
        choices = raw_json.get("choices") or []
        if not choices:
            return ""
        message = choices[0].get("message") or {}
        return message.get("content", "")

    @staticmethod
    def _extract_usage(raw_json: Mapping[str, Any]) -> dict[str, Optional[int]]:
        usage = raw_json.get("usage") or {}
        return {
            "prompt_tokens": usage.get("prompt_tokens"),
            "completion_tokens": usage.get("completion_tokens"),
            "total_tokens": usage.get("total_tokens"),
        }

    @staticmethod
    def _extract_error_code(raw_json: Mapping[str, Any]) -> Optional[str]:
        error = raw_json.get("error")
        if isinstance(error, dict):
            return error.get("code")
        return None

    @staticmethod
    def _read_error_payload(exc: HTTPError) -> dict[str, Any]:
        try:
            raw = exc.read().decode("utf-8")
            return json.loads(raw)
        except Exception:
            return {"detail": "OpenRouter error response could not be parsed."}

    @staticmethod
    async def _read_error_payload_async(response: httpx.Response) -> dict[str, Any]:
        try:
            raw = await response.aread()
            return json.loads(raw.decode("utf-8"))
        except Exception:
            return {"detail": "OpenRouter error response could not be parsed."}
