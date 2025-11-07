# Telegram Persona Bot

A lightweight Python project showcasing an LLM-driven Telegram bot that role-plays as a configurable persona. The bot talks through [OpenRouter](https://openrouter.ai) using an OpenAI-compatible API and keeps short-term memories for each chat.

## Features

- **Smart reply logic**: Always responds in private 1-on-1 chats, uses configurable frequency in groups
- **Emoji reactions**: LLM-powered emoji reactions to messages based on persona and context
- **Auto-summarization**: Automatically summarizes old conversations and stores them as memories when history grows
- **Persistent storage**: Memories and chat history automatically saved to disk and restored on restart
- Adjustable reply frequency, persona, system prompt, and model via Telegram commands.
- Lightweight, file-backed configuration with built-in validation.
- Per-chat memory and history tracking with automatic management.
- Extensible LLM wrapper for OpenRouter-compatible models.
- Async implementation powered by `python-telegram-bot` v20.
- Comprehensive error handling and logging for debugging

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
   export API_KEY="<openrouter-api-key>"
   ```

3. Run the bot:

   ```bash
   python -m tbot.main --api-key "$API_KEY"
   ```

   Or with verbose logging for debugging:

   ```bash
   python -m tbot.main --api-key "$API_KEY" --verbose
   ```

The bot stores its configuration in `~/.tbot-config.json` by default.

## Behavior

- **Private chats**: The bot always responds to messages in private 1-on-1 conversations
- **Group chats**: The bot uses the configured `response_frequency` to decide whether to respond
- **Direct replies**: The bot always responds when you reply to one of its messages (in any chat type)

### Auto-summarization

The bot automatically manages conversation history per chat:

- **History tracking**: Each chat maintains its own separate conversation history
- **Automatic summarization**: When history reaches the threshold (default: 18 messages), the bot:
  1. Takes the oldest messages (default: 10 messages)
  2. Uses the LLM to generate a concise summary
  3. Stores the summary as a memory
  4. Removes the summarized messages from history to save space
- **Memory integration**: Summaries are automatically included in context for future conversations
- **Configuration**: Adjust `summarize_threshold` and `summarize_batch_size` in config, or disable with `auto_summarize_enabled: false`

This ensures the bot can maintain long-term context while keeping the conversation history manageable.

### Data Persistence

All chat data is automatically persisted to disk:

- **Storage location**: `~/.tbot-data.json` (configurable)
- **What's saved**: Memories, conversation history, and summarization counts for all chats
- **Auto-save**: Changes are immediately saved to disk after each modification
- **Auto-load**: Data is automatically loaded when the bot starts
- **Atomic writes**: Uses temporary files to prevent data corruption
- **Per-chat isolation**: Each chat's data is stored and restored independently

The bot maintains continuity across restarts, remembering past conversations and accumulated memories.

### Emoji Reactions

The bot can react to user messages with contextually appropriate emoji:

- **LLM-powered selection**: The bot uses the LLM to suggest reactions based on message content and persona
- **Configurable frequency**: Control how often reactions are added with `reaction_frequency` (default: 0.3 or 30%)
- **Smart suggestions**: The LLM chooses from 75+ common Telegram reactions or suggests no reaction when appropriate
- **Non-critical**: Reaction errors don't interrupt conversations - failures are logged but don't affect replies
- **Persona-aware**: Reactions match the bot's configured persona (e.g., a cheerful bot might use more positive emojis)

Enable/disable reactions with the `reactions_enabled` config setting, or adjust how often they appear with `reaction_frequency`.

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

The tests focus on configuration management, memory handling, reply decision logic, auto-summarization, and data persistence.

## Configuration

The bot stores its configuration in `~/.tbot-config.json`. Here are the available settings:

| Setting | Default | Description |
|---------|---------|-------------|
| `response_frequency` | 0.4 | Probability (0.0-1.0) of responding in group chats |
| `persona` | "An affable research assistant..." | The bot's persona description |
| `system_prompt` | "You are role-playing..." | System prompt for the LLM |
| `llm_model` | "openai/gpt-4o-mini" | OpenRouter model to use |
| `max_context_messages` | 12 | Number of recent messages to include in LLM context |
| `auto_summarize_enabled` | true | Enable/disable automatic summarization |
| `summarize_threshold` | 18 | Number of messages that triggers summarization |
| `summarize_batch_size` | 10 | Number of oldest messages to summarize at once |
| `reactions_enabled` | true | Enable/disable emoji reactions to messages |
| `reaction_frequency` | 0.3 | Probability (0.0-1.0) of adding a reaction to user messages |

You can edit the config file directly or use Telegram commands to update some settings.

