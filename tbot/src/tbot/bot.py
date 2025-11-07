"""Telegram bot wiring for the persona simulator."""
from __future__ import annotations

import asyncio
import logging
import os
import random
from telegram import Message, Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CallbackContext,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from .config import BotConfig, ConfigManager
from .llm_client import LLMClient
from .logic import should_respond
from .memory import MemoryManager

logger = logging.getLogger(__name__)


def _get_message(update: Update) -> Message | None:
    """Return the effective message for an update when available."""

    return update.effective_message


async def _reply_with_config(update: Update, config: BotConfig) -> None:
    message = _get_message(update)
    if message is None:
        return

    text = (
        "<b>Persona bot configuration</b>\n"
        f"Persona: {config.persona}\n"
        f"Response frequency: {config.response_frequency:.2f}\n"
        f"Model: {config.llm_model}\n"
        f"Max context messages: {config.max_context_messages}\n"
    )
    await message.reply_text(text, parse_mode=ParseMode.HTML)


def _parse_argument(update: Update) -> str:
    message = _get_message(update)
    if not message or not message.text:
        return ""
    parts = message.text.split(" ", 1)
    if len(parts) == 1:
        return ""
    return parts[1].strip()


async def _maybe_auto_summarize(
    *,
    chat_id: int,
    config: BotConfig,
    memory_manager: MemoryManager,
    llm_client: LLMClient,
) -> None:
    """Check if history should be summarized and perform summarization if needed.

    Args:
        chat_id: The chat to check
        config: Bot configuration
        memory_manager: Memory manager instance
        llm_client: LLM client for generating summaries
    """
    # Check if auto-summarization is enabled
    if not config.auto_summarize_enabled:
        return

    # Check if threshold is reached
    if not memory_manager.should_summarize(chat_id, config.summarize_threshold):
        return

    logger.info(
        f"Chat {chat_id} reached threshold ({config.summarize_threshold}), "
        "triggering auto-summarization"
    )

    try:
        # Get messages to summarize
        messages_to_summarize, total_size = memory_manager.get_messages_for_summary(
            chat_id, config.summarize_batch_size
        )

        if not messages_to_summarize:
            logger.warning(f"No messages to summarize for chat {chat_id}")
            return

        logger.debug(
            f"Summarizing {len(messages_to_summarize)} oldest messages "
            f"(out of {total_size} total)"
        )

        # Generate summary using LLM
        summary = await llm_client.generate_summary(
            messages=messages_to_summarize,
            persona=config.persona,
            model=config.llm_model,
        )

        # Add summary to memories
        memory_manager.add_memory(
            chat_id, f"[Auto-summary]: {summary}"
        )

        # Clear the summarized messages from history
        memory_manager.clear_summarized_messages(chat_id, len(messages_to_summarize))

        logger.info(
            f"Successfully summarized and stored {len(messages_to_summarize)} messages "
            f"for chat {chat_id}. Summary: {summary[:100]}..."
        )
    except Exception as e:
        # Log error but don't fail the whole conversation
        logger.error(f"Failed to auto-summarize chat {chat_id}: {e}", exc_info=True)


def create_application(
    token: str,
    *,
    api_key: str | None = None,
    config_manager: ConfigManager | None = None,
    memory_manager: MemoryManager | None = None,
    llm_client: LLMClient | None = None,
) -> Application:
    """Create the Telegram application with handlers wired in."""

    config_manager = config_manager or ConfigManager()
    memory_manager = memory_manager or MemoryManager()
    resolved_api_key = api_key or os.getenv("API_KEY")
    llm_client = llm_client or LLMClient(api_key=resolved_api_key)

    application = Application.builder().token(token).build()

    async def handle_persona(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        argument = _parse_argument(update)
        message = _get_message(update)
        if message is None:
            return
        if not argument:
            await message.reply_text("Usage: /persona <description>")
            return
        config_manager.set_field("persona", argument)
        await message.reply_text("Persona updated.")

    async def handle_frequency(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        argument = _parse_argument(update)
        message = _get_message(update)
        if message is None:
            return
        try:
            value = float(argument)
        except ValueError:
            await message.reply_text("Usage: /frequency <0.0-1.0>")
            return
        config_manager.set_field("response_frequency", value)
        await message.reply_text(
            f"Response frequency set to {value:.2f}."
        )

    async def handle_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        argument = _parse_argument(update)
        message = _get_message(update)
        if message is None:
            return
        if not argument:
            await message.reply_text("Usage: /prompt <system prompt>")
            return
        config_manager.set_field("system_prompt", argument)
        await message.reply_text("System prompt updated.")

    async def handle_model(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        argument = _parse_argument(update)
        message = _get_message(update)
        if message is None:
            return
        if not argument:
            await message.reply_text("Usage: /model <model name>")
            return
        config_manager.set_field("llm_model", argument)
        await message.reply_text(f"Model set to {argument}.")

    async def handle_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await _reply_with_config(update, config_manager.config)

    async def handle_memory(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        argument = _parse_argument(update)
        message = _get_message(update)
        if message is None or update.effective_chat is None:
            return
        if not argument:
            await message.reply_text(
                "Usage: /memory <add|clear|list> [text]"
            )
            return
        chat_id = update.effective_chat.id
        parts = argument.split(" ", 1)
        action = parts[0].lower()
        payload = parts[1].strip() if len(parts) > 1 else ""
        if action == "add" and payload:
            entry = memory_manager.add_memory(chat_id, payload)
            await message.reply_text(
                f"Stored memory at {entry.created_at.isoformat()}"
            )
        elif action == "clear":
            memory_manager.clear_memories(chat_id)
            await message.reply_text("Cleared memories for this chat.")
        elif action == "list":
            memories = memory_manager.get_memories(chat_id)
            if not memories:
                await message.reply_text("No memories stored yet.")
            else:
                lines = [f"- {m.text} ({m.created_at:%Y-%m-%d})" for m in memories]
                await message.reply_text("\n".join(lines))
        else:
            await message.reply_text(
                "Usage: /memory <add|clear|list> [text]"
            )

    async def handle_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        message = _get_message(update)
        if message is None:
            return
        await message.reply_text(
            "Available commands:\n"
            "/persona <text> - set persona\n"
            "/frequency <0-1> - adjust reply probability\n"
            "/prompt <text> - set system prompt\n"
            "/model <name> - set OpenRouter model\n"
            "/memory add|list|clear - manage memories\n"
            "/status - show configuration"
        )

    async def maybe_reply(update: Update, context: CallbackContext) -> None:
        message = _get_message(update)
        if message is None or update.effective_chat is None:
            return
        chat_id = update.effective_chat.id
        text = message.text or ""
        if not text:
            return

        memory_manager.append_history(
            chat_id,
            f"{update.effective_user.first_name or 'User'}: {text}",
        )

        config = config_manager.config
        bot_user = context.bot if hasattr(context, "bot") else None
        replied_to_bot = False
        if message.reply_to_message and bot_user:
            replied_to = message.reply_to_message.from_user
            replied_to_bot = replied_to.id == bot_user.id if replied_to else False

        # Detect if this is a private 1-on-1 chat
        is_private_chat = update.effective_chat.type == "private"

        should_reply = should_respond(
            random_value=random.random(),
            response_frequency=config.response_frequency,
            replied_to_bot=replied_to_bot,
            is_private_chat=is_private_chat,
        )

        if not should_reply:
            return

        history = memory_manager.get_history(chat_id, config.max_context_messages)
        memories = memory_manager.get_memories(chat_id)

        try:
            reply = await llm_client.generate_reply(
                config=config,
                history=history,
                memories=memories,
                user_message=text,
            )
            await message.reply_text(reply)
            memory_manager.append_history(chat_id, f"Bot: {reply}")
            logger.info(f"Successfully replied to message in chat {chat_id}")

            # Check if auto-summarization should be triggered
            await _maybe_auto_summarize(
                chat_id=chat_id,
                config=config,
                memory_manager=memory_manager,
                llm_client=llm_client,
            )
        except Exception as e:
            logger.error(f"Failed to generate reply for chat {chat_id}: {e}")
            error_message = (
                "Sorry, I encountered an error generating a response. "
                "Please try again later."
            )
            await message.reply_text(error_message)

    application.add_handler(CommandHandler("persona", handle_persona))
    application.add_handler(CommandHandler("frequency", handle_frequency))
    application.add_handler(CommandHandler("prompt", handle_prompt))
    application.add_handler(CommandHandler("model", handle_model))
    application.add_handler(CommandHandler("status", handle_status))
    application.add_handler(CommandHandler("memory", handle_memory))
    application.add_handler(CommandHandler("help", handle_help))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, maybe_reply)
    )

    return application


async def run_polling(token: str, *, api_key: str | None = None) -> None:
    """Helper entry point for manual runs."""
    application = create_application(token, api_key=api_key)
    async with application:
        await application.start()
        await application.updater.start_polling()
        try:
            while True:
                await asyncio.sleep(3600)
        except asyncio.CancelledError:
            pass
        finally:
            await application.updater.stop()
            await application.stop()

