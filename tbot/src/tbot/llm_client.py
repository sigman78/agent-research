"""OpenAI-compatible client for generating replies via OpenRouter."""
from __future__ import annotations

import asyncio
import logging
from typing import Iterable, List, Optional

try:  # pragma: no cover - imported lazily for tests
    from openai import OpenAI
    from openai import OpenAIError
except Exception:  # pragma: no cover - fallback when package missing
    OpenAI = None  # type: ignore
    OpenAIError = Exception  # type: ignore

from .config import BotConfig
from .memory import MemoryEntry

logger = logging.getLogger(__name__)

# Constants for LLM parameters
DEFAULT_TEMPERATURE = 0.8
DEFAULT_MAX_TOKENS = 512
DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"


class LLMClient:
    """Wrapper around the OpenAI client to talk to OpenRouter."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = DEFAULT_BASE_URL,
        client: Optional[OpenAI] = None,
    ) -> None:
        """Initialize the LLM client.

        Args:
            api_key: OpenRouter-compatible API key
            base_url: Base URL for the API (defaults to OpenRouter)
            client: Optional pre-configured OpenAI client for testing

        Raises:
            RuntimeError: If OpenAI package is not installed
            ValueError: If api_key is not provided when client is None
        """
        if client is not None:
            self._client = client
        else:
            if OpenAI is None:  # pragma: no cover
                raise RuntimeError(
                    "openai package is not installed. "
                    "Install it with: pip install openai"
                )
            if not api_key:
                raise ValueError(
                    "api_key must be provided when client is not specified"
                )
            self._client = OpenAI(api_key=api_key, base_url=base_url)
            logger.info(f"Initialized LLM client with base URL: {base_url}")

    async def generate_reply(
        self,
        config: BotConfig,
        history: Iterable[str],
        memories: Iterable[MemoryEntry],
        user_message: str,
    ) -> str:
        """Generate a reply using the configured LLM.

        Args:
            config: Bot configuration containing model and prompts
            history: Recent conversation history
            memories: Stored memories for the persona
            user_message: The user's current message

        Returns:
            Generated reply text

        Raises:
            OpenAIError: If the API call fails
            ValueError: If the response is invalid or empty
        """
        if not user_message or not user_message.strip():
            raise ValueError("user_message cannot be empty")

        system = f"{config.system_prompt}\nPersona: {config.persona}"
        memory_lines = [f"- {entry.text}" for entry in memories]
        memory_blob = "\n".join(memory_lines) if memory_lines else "None"

        messages: List[dict[str, str]] = [
            {"role": "system", "content": system},
            {
                "role": "system",
                "content": (
                    "Relevant persona memories (optional):\n" f"{memory_blob}"
                ),
            },
        ]
        for item in history:
            messages.append({"role": "user", "content": item})
        messages.append({"role": "user", "content": user_message})

        logger.debug(
            f"Generating reply with model {config.llm_model}, "
            f"{len(messages)} messages in context"
        )

        def _call() -> str:
            try:
                response = self._client.chat.completions.create(
                    model=config.llm_model,
                    messages=messages,
                    temperature=DEFAULT_TEMPERATURE,
                    max_tokens=DEFAULT_MAX_TOKENS,
                )
                content = response.choices[0].message.content
                if content is None:
                    raise ValueError("LLM returned empty response")
                return content.strip()
            except OpenAIError as e:
                error_msg = str(e)
                logger.error(
                    f"API error while generating reply with model '{config.llm_model}': {error_msg}"
                )
                # Provide helpful error messages for common issues
                if "Bad request" in error_msg or "400" in error_msg:
                    logger.error(
                        f"Bad request error. Check that model name '{config.llm_model}' is valid. "
                        "For OpenRouter, use format 'provider/model' (e.g., 'openai/gpt-4o-mini')"
                    )
                raise
            except (IndexError, AttributeError) as e:
                logger.error(f"Invalid response structure from LLM: {e}")
                raise ValueError("Invalid response from LLM") from e

        try:
            reply = await asyncio.to_thread(_call)
            logger.debug(f"Successfully generated reply of length {len(reply)}")
            return reply
        except Exception as e:
            logger.error(f"Failed to generate reply: {e}")
            raise

