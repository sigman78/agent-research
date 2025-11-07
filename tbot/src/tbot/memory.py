"""Simple in-memory store for persona memories and chat history."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)


@dataclass
class MemoryEntry:
    chat_id: int
    text: str
    created_at: datetime


class MemoryManager:
    """Store persona memories and recent chat messages per chat."""

    def __init__(self, history_size: int = 20) -> None:
        self._memories: Dict[int, List[MemoryEntry]] = {}
        self._history: Dict[int, List[str]] = {}
        self._history_size = history_size
        self._summarization_count: Dict[int, int] = {}

    def add_memory(self, chat_id: int, text: str) -> MemoryEntry:
        entry = MemoryEntry(chat_id=chat_id, text=text.strip(), created_at=datetime.utcnow())
        self._memories.setdefault(chat_id, []).append(entry)
        return entry

    def get_memories(self, chat_id: int) -> List[MemoryEntry]:
        return list(self._memories.get(chat_id, []))

    def clear_memories(self, chat_id: int) -> None:
        self._memories.pop(chat_id, None)

    def append_history(self, chat_id: int, message: str) -> None:
        history = self._history.setdefault(chat_id, [])
        history.append(message)
        if len(history) > self._history_size:
            del history[: len(history) - self._history_size]

    def get_history(self, chat_id: int, limit: int | None = None) -> List[str]:
        history = self._history.get(chat_id, [])
        if limit is None:
            return list(history)
        return history[-limit:]

    def should_summarize(self, chat_id: int, threshold: int) -> bool:
        """Check if chat history has reached the summarization threshold.

        Args:
            chat_id: The chat to check
            threshold: Number of messages that triggers summarization

        Returns:
            True if summarization should be triggered
        """
        history = self._history.get(chat_id, [])
        return len(history) >= threshold

    def get_messages_for_summary(
        self, chat_id: int, batch_size: int
    ) -> Tuple[List[str], int]:
        """Get the oldest messages for summarization.

        Args:
            chat_id: The chat to get messages from
            batch_size: Number of messages to summarize

        Returns:
            Tuple of (messages to summarize, total history size)
        """
        history = self._history.get(chat_id, [])
        if not history:
            return [], 0

        # Get the oldest batch_size messages
        messages_to_summarize = history[:batch_size]
        return messages_to_summarize, len(history)

    def clear_summarized_messages(self, chat_id: int, count: int) -> None:
        """Remove the oldest messages from history after they've been summarized.

        Args:
            chat_id: The chat to clear messages from
            count: Number of messages to remove from the beginning
        """
        history = self._history.get(chat_id, [])
        if not history:
            return

        # Remove the oldest 'count' messages
        del history[:count]
        logger.info(f"Cleared {count} summarized messages from chat {chat_id}")

        # Track summarization
        self._summarization_count[chat_id] = (
            self._summarization_count.get(chat_id, 0) + 1
        )

    def get_summarization_count(self, chat_id: int) -> int:
        """Get the number of times history has been summarized for a chat.

        Args:
            chat_id: The chat to check

        Returns:
            Number of summarizations performed
        """
        return self._summarization_count.get(chat_id, 0)

    def get_history_size(self, chat_id: int) -> int:
        """Get the current size of history for a chat.

        Args:
            chat_id: The chat to check

        Returns:
            Number of messages in history
        """
        return len(self._history.get(chat_id, []))

