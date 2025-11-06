"""Simple in-memory store for persona memories and chat history."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List


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

