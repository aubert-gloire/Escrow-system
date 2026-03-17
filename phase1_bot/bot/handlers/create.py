"""
Create Escrow Group Handler — /create command and "Create Escrow Group" button.
"""

import random
import uuid
from datetime import datetime

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from loguru import logger
from motor.motor_asyncio import AsyncIOMotorDatabase

from bot.keyboards import CreateGroupKeyboard, MainMenuKeyboard
from bot.utils.formatters import format_group_welcome
from bot.utils.group_manager import GroupManager
from database.crud import DealCRUD, UserCRUD

router = Router()


def _new_deal_id() -> str:
    return f"DEAL_{uuid.uuid4().hex[:8].upper()}"


def _new_group_number() -> str:
    return str(random.randint(10000, 99999))


async def _handle_create(
    db: AsyncIOMotorDatabase,
    bot: Bot,
    user_id: int,
    username: str,
    respond,
    user_client=None,
):
    """Core logic shared between the /create command and the callback button."""
    deal_id = _new_deal_id()
    group_number = _new_group_number()

    # Register the user if not yet known
    if not await UserCRUD.get_user(db, user_id):
        await UserCRUD.create_user(db, user_id, username, username)

    created = await DealCRUD.create_deal(
        db,
        deal_id=deal_id,
        group_deal_number=group_number,
        creator_id=user_id,
        creator_username=username,
    )
    if not created:
        await respond("❌ Failed to create the deal record. Please try again.")
        return

    group_result = await GroupManager.create_escrow_group(
        user_client, bot, deal_id, group_number
    )

    if group_result.get("success"):
        group_id = group_result["group_id"]
        group_link = group_result["group_link"]

        # Persist group info on the deal
        await db.deals.update_one(
            {"deal_id": deal_id},
            {
                "$set": {
                    "group_id": group_id,
                    "group_link": group_link,
                    "group_created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow(),
                }
            },
        )

        # Post welcome message in the new group
        await bot.send_message(
            chat_id=group_id,
            text=format_group_welcome(group_number),
            parse_mode="Markdown",
        )

        await respond(
            f"✅ *Escrow Group Created!*\n\n"
            f"Group: *Escrow #{group_number}*\n"
            f"Transaction ID: `{deal_id}`\n\n"
            f"Share the invite link below with the other party.\n"
            f"Once both parties join:\n"
            f"  • Seller types `/seller <wallet address>`\n"
            f"  • Buyer types `/buyer <wallet address>`",
            reply_markup=CreateGroupKeyboard.get_join_group(group_link),
            parse_mode="Markdown",
        )
    else:
        # Clean up the orphaned deal stub
        await db.deals.delete_one({"deal_id": deal_id})
        await respond(
            f"❌ *Could not create Telegram group.*\n\n"
            f"Error: `{group_result.get('error', 'Unknown error')}`\n\n"
            f"Please ensure the Telethon session is configured and contact admin.",
            parse_mode="Markdown",
        )


@router.message(Command("create"))
async def cmd_create(
    message: Message,
    db: AsyncIOMotorDatabase,
    bot: Bot,
    user_client=None,
):
    user = message.from_user
    username = user.username or f"user_{user.id}"

    async def respond(text, **kwargs):
        await message.answer(text, **kwargs)

    await _handle_create(db, bot, user.id, username, respond, user_client)


@router.callback_query(F.data == "create_deal")
async def callback_create_deal(
    callback: CallbackQuery,
    db: AsyncIOMotorDatabase,
    bot: Bot,
    user_client=None,
):
    user = callback.from_user
    username = user.username or f"user_{user.id}"
    await callback.answer()

    async def respond(text, **kwargs):
        await callback.message.answer(text, **kwargs)

    await _handle_create(db, bot, user.id, username, respond, user_client)
