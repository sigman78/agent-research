"""OpenAI-compatible client for generating replies via OpenRouter."""
from __future__ import annotations

import asyncio
from typing import Iterable, List, Optional

try:  # pragma: no cover - imported lazily for tests
    from openai import OpenAI
except Exception:  # pragma: no cover - fallback when package missing
    OpenAI = None  # type: ignore

from .config import BotConfig
from .memory import MemoryEntry


class LLMClient:
    """Wrapper around the OpenAI client to talk to OpenRouter."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = "https://openrouter.ai/api/v1",
        client: Optional[OpenAI] = None,
    ) -> None:
        if client is not None:
            self._client = client
        else:
            if OpenAI is None:  # pragma: no cover
                raise RuntimeError("openai package is not installed")
            self._client = OpenAI(api_key=api_key, base_url=base_url)

    async def generate_reply(
        self,
        config: BotConfig,
        history: Iterable[str],
        memories: Iterable[MemoryEntry],
        user_message: str,
    ) -> str:
        """Generate a reply using the configured LLM."""

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

        def _call() -> str:
            response = self._client.chat.completions.create(
                model=config.llm_model,
                messages=messages,
                temperature=0.8,
                max_tokens=512,
            )
            return response.choices[0].message.content.strip()  # type: ignore[attr-defined]

        return await asyncio.to_thread(_call)

