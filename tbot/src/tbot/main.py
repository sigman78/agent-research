"""CLI entry point for running the Telegram persona bot."""
from __future__ import annotations

import argparse
import asyncio
import os


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the persona Telegram bot")
    parser.add_argument(
        "--token",
        default=os.getenv("TELEGRAM_BOT_TOKEN"),
        help="Telegram bot token (or set TELEGRAM_BOT_TOKEN env var)",
    )
    parser.add_argument(
        "--api-key",
        default=os.getenv("API_KEY"),
        help="OpenRouter-compatible API key (or set API_KEY env var)",
    )
    return parser.parse_args()


def main() -> None:
    from .bot import run_polling

    args = parse_args()
    if not args.token:
        raise SystemExit("Telegram bot token is required. Use --token or TELEGRAM_BOT_TOKEN.")
    if not args.api_key:
        raise SystemExit("API key is required. Use --api-key or API_KEY.")
    asyncio.run(run_polling(args.token, api_key=args.api_key))


if __name__ == "__main__":
    main()

