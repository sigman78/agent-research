from __future__ import annotations

from tbot.logic import should_respond


def test_should_respond_respects_frequency() -> None:
    assert should_respond(random_value=0.1, response_frequency=0.2, replied_to_bot=False)
    assert not should_respond(random_value=0.5, response_frequency=0.2, replied_to_bot=False)


def test_should_respond_prioritises_replies() -> None:
    assert should_respond(random_value=0.9, response_frequency=0.1, replied_to_bot=True)

