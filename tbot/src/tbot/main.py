"""CLI entry point for running the Telegram persona bot."""
from __future__ import annotations

import argparse
import asyncio
import os

from .bot import run_polling


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the persona Telegram bot")
    parser.add_argument(
        "--token",
        default=os.getenv("TELEGRAM_BOT_TOKEN"),
        help="Telegram bot token (or set TELEGRAM_BOT_TOKEN env var)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.token:
        raise SystemExit("Telegram bot token is required. Use --token or TELEGRAM_BOT_TOKEN.")
    asyncio.run(run_polling(args.token))


if __name__ == "__main__":
    main()

