# Telegram Persona Bot

A lightweight Python project showcasing an LLM-driven Telegram bot that role-plays as a configurable persona. The bot talks through [OpenRouter](https://openrouter.ai) using an OpenAI-compatible API and keeps short-term memories for each chat.

## Features

- Adjustable reply frequency, persona, system prompt, and model via Telegram commands.
- Lightweight, file-backed configuration with built-in validation.
- In-memory persona memories and chat history with easy management commands.
- Extensible LLM wrapper for OpenRouter-compatible models.
- Async implementation powered by `python-telegram-bot` v20.

## Setup

1. Install dependencies (preferably in a virtual environment):

   ```bash
   cd /path/to/repo/tbot
   pip install -r requirements-dev.txt
   ```

   Alternatively, run the helper script from the repo root:

   ```bash
   ./tbot/scripts/install_deps.sh
   ```

2. Export your credentials:

   ```bash
   export TELEGRAM_BOT_TOKEN="<telegram-token>"
   export OPENROUTER_API_KEY="<openrouter-key>"
   ```

3. Run the bot:

   ```bash
   python -m tbot.main
   ```

The bot stores its configuration in `~/.tbot-config.json` by default.

## Telegram commands

- `/persona <text>` – set the bot's persona description.
- `/frequency <0-1>` – control how often the bot answers unsolicited messages.
- `/prompt <text>` – update the system prompt injected before LLM calls.
- `/model <name>` – choose a different OpenRouter model.
- `/memory add|list|clear` – manage stored memories for the current chat.
- `/status` – show current configuration values.
- `/help` – show a summary of available commands.

## Tests

Run the automated test suite with:

```bash
pytest
```

The tests focus on configuration management, memory handling, and reply decision logic.

