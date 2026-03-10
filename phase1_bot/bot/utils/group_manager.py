"""
Telegram Group Management using Telethon user client.

The Telegram Bot API does not allow bots to create groups/chats.
Group creation requires a user-level account authenticated via Telethon.
See bot/utils/telegram_client.py and generate_session.py for setup.
"""

from aiogram import Bot
from telethon import TelegramClient
from telethon.tl.functions.channels import (
    CreateChannelRequest,
    InviteToChannelRequest,
    EditAdminRequest,
)
from telethon.tl.functions.messages import ExportChatInviteRequest
from telethon.tl.types import ChatAdminRights
from config.settings import settings
from loguru import logger
from typing import Optional, Dict, Any


class GroupManager:
    """Manage escrow group creation and messaging."""

    @staticmethod
    async def create_group_for_deal(
        user_client: Optional[TelegramClient],
        bot: Bot,
        deal_id: str,
        amount: float,
        currency: str,
        description: str,
    ) -> Dict[str, Any]:
        """
        Create a Telegram supergroup for an escrow deal.

        Uses the Telethon user client to:
          1. Create the supergroup
          2. Add the bot as a member
          3. Promote the bot to admin
          4. Export an invite link

        Returns dict with keys: success, group_id, group_link (or error).
        """
        if user_client is None or not user_client.is_connected():
            logger.warning(f"User client unavailable — skipping group creation for {deal_id}")
            return {"error": "Telethon user client not configured", "success": False}

        try:
            group_title = f"🔒 Escrow {deal_id}"

            # 1. Create supergroup (megagroup=True → group, not broadcast channel)
            result = await user_client(CreateChannelRequest(
                title=group_title,
                about=f"Escrow Deal #{deal_id} | {amount} {currency} | {description[:100]}",
                megagroup=True,
            ))
            group = result.chats[0]

            # Convert Telethon's bare group ID to the signed 64-bit format used by aiogram
            group_chat_id = int(f"-100{group.id}")
            logger.info(f"Created supergroup {group_chat_id} ('{group_title}') for deal {deal_id}")

            # 2. Resolve the bot entity (need its username to add it)
            bot_info = await bot.get_me()
            if not bot_info.username:
                raise ValueError("Bot has no username set — cannot add to group")
            bot_entity = await user_client.get_entity(bot_info.username)

            # 3. Add the bot to the group
            await user_client(InviteToChannelRequest(channel=group, users=[bot_entity]))
            logger.info(f"Added bot @{bot_info.username} to group {group_chat_id}")

            # 4. Promote the bot to admin
            await user_client(EditAdminRequest(
                channel=group,
                user_id=bot_entity,
                admin_rights=ChatAdminRights(
                    change_info=True,
                    post_messages=True,
                    edit_messages=True,
                    delete_messages=True,
                    ban_users=True,
                    invite_users=True,
                    pin_messages=True,
                    add_admins=False,
                    manage_call=False,
                ),
                rank="Escrow Bot",
            ))
            logger.info(f"Promoted bot to admin in group {group_chat_id}")

            # 5. Export an invite link
            invite = await user_client(ExportChatInviteRequest(peer=group))
            invite_link = invite.link

            return {
                "group_id": group_chat_id,
                "group_link": invite_link,
                "success": True,
            }

        except Exception as e:
            logger.error(f"Error creating group for deal {deal_id}: {e}")
            return {"error": str(e), "success": False}

    @staticmethod
    async def post_deal_info_to_group(
        bot: Bot,
        group_id: int,
        deal: Dict[str, Any],
    ) -> bool:
        """Post the full deal details into the group via the bot."""
        try:
            text = (
                f"*🔒 ESCROW DEAL #{deal.get('deal_id')}*\n\n"
                f"*Amount:* {deal.get('amount')} {deal.get('currency')}\n"
                f"*Description:* {deal.get('description')}\n\n"
                f"*Buyer:* @{deal.get('buyer_username')}\n"
                f"*Seller:* @{deal.get('seller_username', 'Waiting...')}\n\n"
                f"*Status:* {deal.get('status')}\n\n"
                f"*Escrow Address:*\n"
                f"```\n{deal.get('escrow_address')}\n```\n"
                f"_tap to copy_\n\n"
                f"Use the bot to manage this deal."
            )
            await bot.send_message(chat_id=group_id, text=text, parse_mode="Markdown")
            return True
        except Exception as e:
            logger.error(f"Error posting deal info to group {group_id}: {e}")
            return False

    @staticmethod
    async def send_group_message(
        bot: Bot,
        group_id: int,
        message: str,
        parse_mode: str = "Markdown",
    ) -> bool:
        """Send an arbitrary message to the group via the bot."""
        try:
            await bot.send_message(chat_id=group_id, text=message, parse_mode=parse_mode)
            return True
        except Exception as e:
            logger.error(f"Error sending group message to {group_id}: {e}")
            return False
