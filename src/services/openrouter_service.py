import json
import os
import threading
import itertools
from typing import Any, Mapping, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

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
    ) -> dict[str, Any]:
        base_url, api_keys = OpenRouterService._get_openrouter_config()
        api_key = OpenRouterService._select_api_key(api_keys)

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
