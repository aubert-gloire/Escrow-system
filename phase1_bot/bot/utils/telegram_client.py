"""
Telethon User Client Manager

A bot cannot create groups/chats via the Telegram Bot API.
This module provides a Telethon user-account client that runs alongside
the aiogram bot to handle group creation for each escrow deal.

Setup:
    1. Run `python generate_session.py` once locally.
    2. Copy the printed TELEGRAM_SESSION_STRING into your .env file.
    3. Set TELEGRAM_API_ID and TELEGRAM_API_HASH from https://my.telegram.org/apps
"""

from telethon import TelegramClient
from telethon.sessions import StringSession
from config.settings import settings
from loguru import logger
from typing import Optional


class UserClient:
    """Manages the singleton Telethon user client."""

    _client: Optional[TelegramClient] = None

    @classmethod
    async def connect(cls) -> Optional[TelegramClient]:
        """
        Connect the Telethon user client.
        Returns the client if successful, None if not configured or auth fails.
        """
        if not settings.telegram_api_id or not settings.telegram_api_hash:
            logger.warning(
                "⚠️  TELEGRAM_API_ID / TELEGRAM_API_HASH not set — group creation disabled."
            )
            return None

        if not settings.telegram_session_string:
            logger.warning(
                "⚠️  TELEGRAM_SESSION_STRING not set — group creation disabled. "
                "Run `python generate_session.py` to create one."
            )
            return None

        try:
            cls._client = TelegramClient(
                StringSession(settings.telegram_session_string),
                int(settings.telegram_api_id),
                settings.telegram_api_hash,
            )
            await cls._client.connect()

            if not await cls._client.is_user_authorized():
                logger.error(
                    "❌ Telethon session is no longer authorized. "
                    "Re-run `python generate_session.py` to refresh it."
                )
                cls._client = None
                return None

            me = await cls._client.get_me()
            logger.info(f"✅ Telethon user client connected as @{me.username} ({me.id})")
            return cls._client

        except Exception as e:
            logger.error(f"❌ Failed to connect Telethon user client: {e}")
            cls._client = None
            return None

    @classmethod
    async def disconnect(cls):
        """Disconnect and clean up the Telethon client."""
        if cls._client and cls._client.is_connected():
            await cls._client.disconnect()
            logger.info("✅ Telethon user client disconnected")
        cls._client = None
