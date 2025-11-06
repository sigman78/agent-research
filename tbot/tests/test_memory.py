from __future__ import annotations

from tbot.memory import MemoryManager


def test_memory_manager_stores_entries() -> None:
    manager = MemoryManager(history_size=3)
    entry = manager.add_memory(1, "Loves hiking")
    assert entry.text == "Loves hiking"
    assert manager.get_memories(1)[0].text == "Loves hiking"

    manager.append_history(1, "User: Hello")
    manager.append_history(1, "Bot: Hi")
    manager.append_history(1, "User: How are you?")
    manager.append_history(1, "Bot: Great!")

    history = manager.get_history(1)
    assert history == [
        "Bot: Hi",
        "User: How are you?",
        "Bot: Great!",
    ]

