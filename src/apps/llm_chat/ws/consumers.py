import json
import logging
import asyncio
from decimal import Decimal
from uuid import UUID
from typing import Any, Optional

from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async

from common.exceptions import OpenRouterError, DomainError
from repositories import LLMChatRepository
from selectors_layer import LLMChatSelectors
from services import OpenRouterService
from apps.llm_chat.models import LLMModel, UserProviderCredential

logger = logging.getLogger("app.ws.chat_consumer")


class ChatConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for authenticated, real-time LLM chat with token streaming.
    
    Expects JSON events:
    {
        "type": "send",
        "payload": {
            "conversation_id": "<uuid>",
            "content": "user message",
            "model_slug": "gpt-4" (optional),
            "credential_id": "<uuid>" (optional)
        }
    }
    
    Sends back:
    - {"type": "assistant.delta", "delta": "token..."}
    - {"type": "assistant.done", "message_id": "<uuid>", "usage": {...}}
    - {"type": "assistant.error", "error": "error message"}
    """

    async def connect(self):
        """
        Authenticate user and accept WebSocket connection.
        Rejects if not authenticated.
        """
        user = self.scope.get("user")
        
        if not user or not user.is_authenticated:
            logger.info("Rejecting unauthenticated WebSocket connection")
            await self.close(code=4001)  # 4001 = Unauthorized
            return
        
        self.user = user
        await self.accept()
        logger.info(f"User {user.id} ({user.phone_number}) connected to chat WebSocket")

    async def disconnect(self, close_code):
        """
        Handle WebSocket disconnection.
        """
        user_info = getattr(self, "user", None)
        if user_info:
            logger.info(f"User {user_info.id} ({user_info.phone_number}) disconnected from chat WebSocket (code: {close_code})")
        else:
            logger.info(f"Unauthenticated connection disconnected (code: {close_code})")

    async def receive_json(self, content: dict[str, Any]):
        """
        Receive and handle JSON messages from client.
        """
        try:
            message_type = content.get("type")
            
            if message_type == "send":
                await self.handle_send(content.get("payload", {}))
            else:
                await self.send_error(f"Unknown message type: {message_type}")
        except Exception as exc:
            logger.exception(f"Error in receive_json: {exc}")
            await self.send_error(f"Unexpected error: {str(exc)}")

    async def handle_send(self, payload: dict[str, Any]):
        """
        Handle user sending a message:
        1. Validate conversation ownership
        2. Store user message
        3. Stream LLM response
        4. Store assistant message with usage
        """
        try:
            # Extract and validate payload
            conversation_id_raw = payload.get("conversation_id")
            content = payload.get("content", "").strip()
            model_slug = payload.get("model_slug")
            credential_id_raw = payload.get("credential_id")
            
            if not conversation_id_raw:
                await self.send_error("Missing conversation_id")
                return
            
            if not content:
                await self.send_error("Missing or empty content")
                return
            
            # Parse IDs
            try:
                conversation_id = UUID(str(conversation_id_raw))
            except (ValueError, TypeError):
                await self.send_error("Invalid conversation_id format")
                return
            
            credential_id = None
            if credential_id_raw:
                try:
                    credential_id = UUID(str(credential_id_raw))
                except (ValueError, TypeError):
                    await self.send_error("Invalid credential_id format")
                    return
            
            # Validate conversation ownership and get conversation
            conversation = await self._get_user_conversation(conversation_id)
            if not conversation:
                await self.send_error("Conversation not found or you do not have access")
                return
            
            # Store user message
            user_message = await self._create_user_message(conversation, content)
            logger.info(f"User {self.user.id} created message {user_message.id} in conversation {conversation.id}")
            
            # Determine model to use
            model = None
            if model_slug:
                model = await self._get_active_model_by_slug(model_slug)
                if not model:
                    await self.send_error(f"Model {model_slug} not found or is inactive")
                    return
            else:
                # Try user preference
                pref = await self._get_user_preferences()
                if pref and pref.default_model and pref.default_model.provider.is_active:
                    model = pref.default_model
                else:
                    # Fall back to first active model
                    model = await self._get_first_active_model()
            
            if not model:
                await self.send_error("No active model available. Please configure a default model.")
                return
            
            # Get credential if specified
            credential = None
            if credential_id:
                credential = await self._get_user_credential(credential_id, model.provider_id)
                if not credential or not credential.is_active:
                    await self.send_error("Credential not found, inactive, or does not belong to this provider")
                    return
            
            # Build message context (conversation history)
            messages_context = await self._build_message_context(conversation)
            
            # Stream LLM response
            await self._stream_and_store_response(
                conversation=conversation,
                model=model,
                credential=credential,
                messages_context=messages_context,
            )
        except DomainError as exc:
            logger.warning(f"Domain error in handle_send: {exc}")
            await self.send_error(str(exc))
        except Exception as exc:
            logger.exception(f"Unexpected error in handle_send: {exc}")
            await self.send_error(f"Failed to process message: {str(exc)}")

    async def _stream_and_store_response(
        self,
        conversation: Any,
        model: LLMModel,
        credential: Optional[UserProviderCredential],
        messages_context: list[dict[str, Any]],
    ):
        """
        Stream LLM response tokens and store the complete message with usage.
        """
        assistant_text = ""
        usage_data = None
        raw_response = None
        error_data = None
        
        try:
            # Stream tokens from OpenRouter
            async for chunk in self._stream_openrouter(
                model_slug=model.slug,
                messages=messages_context,
            ):
                # Handle error chunks
                if "error" in chunk:
                    error_info = chunk["error"]
                    error_data = {
                        "code": error_info.get("error_code", "openrouter_error"),
                        "message": f"OpenRouter error: {error_info.get('error_code', 'unknown')}",
                    }
                    await self.send_error(error_data["message"])
                    return
                
                # Extract delta and send to client
                delta = chunk.get("delta", "")
                if delta:
                    assistant_text += delta
                    await self.send_json({
                        "type": "assistant.delta",
                        "delta": delta,
                    })
                
                # Store usage info from final chunk
                if "usage" in chunk:
                    usage_data = chunk["usage"]
                    raw_response = chunk.get("raw")
            
            # Compute costs from usage
            cost_data = await self._compute_costs(model, usage_data or {})
            
            # Store assistant message with usage and cost
            assistant_message = await self._create_assistant_message(
                conversation=conversation,
                content=assistant_text,
                model=model,
                credential=credential,
                usage=usage_data or {},
                cost=cost_data,
                raw_response=raw_response,
                error=None,
            )
            
            logger.info(f"Created assistant message {assistant_message.id} with {usage_data.get('total_tokens', 'unknown') if usage_data else 'unknown'} tokens")
            
            # Send completion event with usage
            await self.send_json({
                "type": "assistant.done",
                "message_id": str(assistant_message.id),
                "usage": {
                    "promptTokens": usage_data.get("prompt_tokens") if usage_data else None,
                    "completionTokens": usage_data.get("completion_tokens") if usage_data else None,
                    "totalTokens": usage_data.get("total_tokens") if usage_data else None,
                },
                "cost": {
                    "inputCost": str(cost_data.get("input_cost") or 0),
                    "outputCost": str(cost_data.get("output_cost") or 0),
                    "totalCost": str(cost_data.get("total_cost") or 0),
                },
            })
        except OpenRouterError as exc:
            logger.exception(f"OpenRouter error: {exc}")
            error_msg = f"LLM service error: {exc.error_code or 'unknown error'}"
            await self.send_error(error_msg)
        except Exception as exc:
            logger.exception(f"Error in _stream_and_store_response: {exc}")
            await self.send_error(f"Error streaming response: {str(exc)}")

    async def send_error(self, error_message: str):
        """
        Send error message to client.
        """
        try:
            await self.send_json({
                "type": "assistant.error",
                "error": error_message,
            })
        except Exception as exc:
            logger.exception(f"Error sending error message: {exc}")

    # ====================================================================
    # DATABASE SYNC HELPERS (bridge async consumer to sync Django ORM)
    # ====================================================================

    @database_sync_to_async
    def _get_user_conversation(self, conversation_id: UUID):
        """
        Get conversation if it belongs to the current user.
        Returns None if not found or not owned by user.
        """
        try:
            return LLMChatSelectors.get_user_conversation_detail(self.user, conversation_id)
        except Exception as exc:
            logger.exception(f"Error fetching conversation {conversation_id}: {exc}")
            return None

    @database_sync_to_async
    def _create_user_message(self, conversation: Any, content: str):
        """
        Create and store a user message.
        """
        return LLMChatRepository.create_user_message(
            conversation=conversation,
            content=content,
            user=self.user,
        )

    @database_sync_to_async
    def _get_active_model_by_slug(self, slug: str) -> Optional[LLMModel]:
        """
        Get an active LLM model by slug.
        Returns None if not found or inactive.
        """
        try:
            return (
                LLMModel.objects.filter(
                    slug=slug,
                    is_active=True,
                    provider__is_active=True,
                )
                .select_related("provider")
                .first()
            )
        except Exception as exc:
            logger.exception(f"Error fetching model {slug}: {exc}")
            return None

    @database_sync_to_async
    def _get_user_preferences(self):
        """
        Get user's LLM preferences (default model/credential).
        """
        try:
            return LLMChatSelectors.get_user_preferences(self.user)
        except Exception as exc:
            logger.exception(f"Error fetching preferences: {exc}")
            return None

    @database_sync_to_async
    def _get_first_active_model(self) -> Optional[LLMModel]:
        """
        Get the first active LLM model (fallback if no default).
        """
        try:
            return LLMChatSelectors.list_active_models().first()
        except Exception as exc:
            logger.exception(f"Error fetching first active model: {exc}")
            return None

    @database_sync_to_async
    def _get_user_credential(
        self,
        credential_id: UUID,
        provider_id: UUID,
    ) -> Optional[UserProviderCredential]:
        """
        Get a user's credential if it belongs to the specified provider.
        Returns None if not found, inactive, or invalid.
        """
        try:
            return UserProviderCredential.objects.filter(
                id=credential_id,
                user=self.user,
                provider_id=provider_id,
                is_active=True,
            ).first()
        except Exception as exc:
            logger.exception(f"Error fetching credential {credential_id}: {exc}")
            return None

    @database_sync_to_async
    def _build_message_context(self, conversation: Any) -> list[dict[str, Any]]:
        """
        Build conversation history for LLM context.
        Returns list of {"role": "...", "content": "..."} dicts.
        """
        try:
            messages = LLMChatSelectors.list_messages(conversation)
            context = []
            # Include all previous messages in order
            for msg in messages:
                context.append({
                    "role": msg.role,
                    "content": msg.content,
                })
            # Add user's current message to context
            # Note: The latest user message was already stored above
            return context
        except Exception as exc:
            logger.exception(f"Error building message context: {exc}")
            return []

    @database_sync_to_async
    def _compute_costs(
        self,
        model: LLMModel,
        usage: dict[str, Any],
    ) -> dict[str, Decimal]:
        """
        Compute input/output/total costs based on model pricing and usage.
        For now, returns zero costs (could be extended with model-specific pricing).
        """
        try:
            input_cost = Decimal(0)
            output_cost = Decimal(0)
            
            return {
                "input_cost": input_cost,
                "output_cost": output_cost,
                "total_cost": input_cost + output_cost,
            }
        except Exception as exc:
            logger.exception(f"Error computing costs: {exc}")
            return {
                "input_cost": Decimal(0),
                "output_cost": Decimal(0),
                "total_cost": Decimal(0),
            }

    @database_sync_to_async
    def _create_assistant_message(
        self,
        conversation: Any,
        content: str,
        model: LLMModel,
        credential: Optional[UserProviderCredential],
        usage: dict[str, Any],
        cost: dict[str, Decimal],
        raw_response: Optional[dict[str, Any]],
        error: Optional[dict[str, Any]],
    ):
        """
        Create and store an assistant message with usage and cost data.
        """
        return LLMChatRepository.create_assistant_message(
            conversation=conversation,
            content=content,
            model_used=model,
            usage=usage,
            cost={
                "input_cost": cost.get("input_cost"),
                "output_cost": cost.get("output_cost"),
                "total_cost": cost.get("total_cost"),
            },
            raw_response=raw_response,
            error=error,
            user=self.user,
        )

    # ====================================================================
    # ASYNC STREAMING HELPERS
    # ====================================================================

    async def _stream_openrouter(
        self,
        model_slug: str,
        messages: list[dict[str, Any]],
    ):
        """
        Stream LLM response tokens using OpenRouter API.
        Yields chunks: {"delta": "...", "usage": {...}, "raw": {...}} or {"error": {...}}
        """
        # Run blocking OpenRouter call in thread pool
        result_generator = await self._run_in_executor(
            OpenRouterService.chat_completion_stream,
            model_slug,
            messages,
        )
        
        # Yield each chunk from the generator
        for chunk in result_generator:
            yield chunk

    async def _run_in_executor(self, func, *args):
        """
        Run a blocking function (OpenRouter generator) in thread pool.
        Returns the generator/result.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, func, *args)
