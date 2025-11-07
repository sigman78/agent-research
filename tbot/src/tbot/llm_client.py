"""OpenAI-compatible client for generating replies via OpenRouter."""
from __future__ import annotations

import asyncio
import logging
from typing import Iterable, List, Optional, cast

try:  # pragma: no cover - imported lazily for tests
    from openai import OpenAI, OpenAIError
    from openai.types.chat import ChatCompletionMessageParam
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

# Common Telegram emoji reactions
COMMON_REACTIONS = [
    "👍", "👎", "❤️", "🔥", "🥰", "👏", "😁", "🤔",
    "🤯", "😱", "🤬", "😢", "🎉", "🤩", "🤮", "💩",
    "🙏", "👌", "🕊", "🤡", "🥱", "🥴", "😍", "🐳",
    "❤‍🔥", "🌚", "🌭", "💯", "🤣", "⚡", "🍌", "🏆",
    "💔", "🤨", "😐", "🍓", "🍾", "💋", "🖕", "😈",
    "😴", "😭", "🤓", "👻", "👨‍💻", "👀", "🎃", "🙈",
    "😇", "😨", "🤝", "✍", "🤗", "🫡", "🎅", "🎄",
    "☃", "💅", "🤪", "🗿", "🆒", "💘", "🙉", "🦄",
    "😘", "💊", "🙊", "😎", "👾", "🤷‍♂", "🤷", "🤷‍♀",
    "😡"
]


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

        messages: List[ChatCompletionMessageParam] = [
            {"role": "system", "content": system},
            {
                "role": "system",
                "content": (f"Relevant persona memories (optional):\n{memory_blob}"),
            },
        ]
        for item in history:
            if item.startswith("Bot: "):
                # Process bot messages - strip the "Bot:" prefix
                clean_content = item[5:]  # Remove "Bot: " prefix
                messages.append({"role": "assistant", "content": clean_content})
            else:
                # Process user messages - strip any user prefix like "User: "
                content = item
                if ": " in content:
                    parts = content.split(": ", 1)
                    if len(parts) > 1:
                        content = parts[1]  # Take only the message part
                messages.append({"role": "user", "content": content})

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

    async def generate_summary(
        self,
        messages: List[str],
        persona: str,
        model: str,
    ) -> str:
        """Generate a concise summary of conversation history.

        Args:
            messages: List of chat messages to summarize
            persona: The bot's persona for context
            model: LLM model to use for summarization

        Returns:
            Concise summary of the conversation

        Raises:
            OpenAIError: If the API call fails
            ValueError: If the response is invalid or empty
        """
        if not messages:
            raise ValueError("Cannot summarize empty message list")

        # Create a specialized prompt for summarization
        messages_text = "\n".join(messages)
        system_prompt = (
            "You are a helpful assistant that creates concise summaries of chat conversations. "
            f"The bot's persona is: {persona}. "
            "Summarize the key points, topics discussed, and important information from the conversation. "
            "Focus on facts, decisions, and context that would be useful to remember in future conversations. "
            "Keep the summary concise (2-4 sentences)."
        )

        summary_messages: List[ChatCompletionMessageParam] = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": f"Please summarize the following conversation:\n\n{messages_text}",
            },
        ]

        logger.debug(f"Generating summary for {len(messages)} messages")

        def _call() -> str:
            try:
                response = self._client.chat.completions.create(
                    model=model,
                    messages=summary_messages,
                    temperature=0.3,  # Lower temperature for more focused summaries
                    max_tokens=256,  # Shorter response for summaries
                )
                content = response.choices[0].message.content
                if content is None:
                    raise ValueError("LLM returned empty summary")
                return content.strip()
            except OpenAIError as e:
                error_msg = str(e)
                logger.error(f"API error while generating summary with model '{model}': {error_msg}")
                raise
            except (IndexError, AttributeError) as e:
                logger.error(f"Invalid response structure from LLM: {e}")
                raise ValueError("Invalid response from LLM") from e

        try:
            summary = await asyncio.to_thread(_call)
            logger.info(f"Successfully generated summary of length {len(summary)}")
            return summary
        except Exception as e:
            logger.error(f"Failed to generate summary: {e}")
            raise

    async def suggest_reaction(
        self,
        message: str,
        persona: str,
        model: str,
    ) -> str | None:
        """Suggest an appropriate emoji reaction for a message.

        Args:
            message: The user's message to react to
            persona: The bot's persona for context
            model: LLM model to use

        Returns:
            An emoji reaction string, or None if no reaction is needed

        Raises:
            OpenAIError: If the API call fails
        """
        if not message or not message.strip():
            return None

        # Create a specialized prompt for reaction selection
        reactions_list = ", ".join(COMMON_REACTIONS[:20])  # Use top 20 most common
        system_prompt = (
            f"You are a helpful assistant that suggests emoji reactions. "
            f"The bot's persona is: {persona}. "
            f"Based on the message, suggest ONE emoji reaction that would be appropriate, "
            f"or respond with 'NONE' if no reaction is needed. "
            f"Available reactions: {reactions_list}. "
            f"Respond with ONLY the emoji or 'NONE', nothing else."
        )

        reaction_messages: List[ChatCompletionMessageParam] = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": f"Message: {message}\n\nSuggest reaction:",
            },
        ]

        logger.debug(f"Requesting reaction suggestion for message: {message[:50]}...")

        def _call() -> str | None:
            try:
                response = self._client.chat.completions.create(
                    model=model,
                    messages=reaction_messages,
                    temperature=0.5,  # Lower temperature for more consistent reactions
                    max_tokens=10,  # Very short response
                )
                content = response.choices[0].message.content
                if content is None:
                    return None
                content = content.strip()

                # Check if LLM suggested no reaction
                if content.upper() == "NONE" or not content:
                    return None

                # Return the suggested emoji
                return content
            except OpenAIError as e:
                logger.error(f"API error while suggesting reaction: {e}")
                return None  # Fail gracefully for reactions
            except Exception as e:
                logger.error(f"Error suggesting reaction: {e}")
                return None

        try:
            reaction = await asyncio.to_thread(_call)
            if reaction:
                logger.debug(f"Suggested reaction: {reaction}")
            return reaction
        except Exception as e:
            logger.error(f"Failed to suggest reaction: {e}")
            return None  # Fail gracefully

