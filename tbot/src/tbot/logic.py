"""Utility functions for bot decision making."""
from __future__ import annotations


def should_respond(
    *,
    random_value: float,
    response_frequency: float,
    replied_to_bot: bool,
) -> bool:
    """Determine whether the bot should reply to a message."""

    if replied_to_bot:
        return True
    frequency = min(max(response_frequency, 0.0), 1.0)
    return random_value <= frequency

