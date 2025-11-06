from __future__ import annotations

from pathlib import Path

from tbot.config import BotConfig, ConfigManager


def test_config_manager_roundtrip(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    manager = ConfigManager(path=config_path)
    manager.set_field("persona", "A curious cat.")
    manager.set_field("response_frequency", 0.9)

    loaded = ConfigManager(path=config_path).config
    assert loaded.persona == "A curious cat."
    assert loaded.response_frequency == 0.9


def test_bot_config_validation() -> None:
    config = BotConfig(persona="  Explorer  ")
    assert config.persona == "Explorer"
    assert config.max_context_messages == 12

