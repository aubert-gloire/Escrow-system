"""
Delivery and Completion Handler
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from motor.motor_asyncio import AsyncIOMotorDatabase
from database.crud import DealCRUD
from bot.keyboards import MainMenuKeyboard, DealActionKeyboard
from bot.utils.formatters import Formatters
from loguru import logger


router = Router()


@router.message(Command("delivered"))
async def cmd_delivered(message: Message, db: AsyncIOMotorDatabase):
    """Handle /delivered command. Usage: /delivered <deal_id>"""
    try:
        args = message.text.split()
        user_id = message.from_user.id

        if len(args) < 2:
            # Show list of deposited deals for this seller
            deals = await DealCRUD.get_user_deals(db, user_id, "seller")
            deposited = [d for d in deals if d.get("status") == "DEPOSITED"]

            if not deposited:
                await message.answer(
                    "❌ No deals awaiting delivery.\n\n"
                    "Usage: `/delivered DEAL_XXXXXXXX`",
                    parse_mode="Markdown"
                )
                return

            deals_list = "\n".join(
                f"• `{d['deal_id']}` — {d['amount']} {d['currency']} — {d['description'][:40]}"
                for d in deposited
            )
            await message.answer(
                f"🚚 *Your Deposited Deals:*\n\n{deals_list}\n\n"
                f"Reply with: `/delivered DEAL_XXXXXXXX`",
                parse_mode="Markdown"
            )
            return

        deal_id = args[1].upper()
        deal = await DealCRUD.get_deal(db, deal_id)

        if not deal:
            await message.answer(f"❌ Deal `{deal_id}` not found.", parse_mode="Markdown")
            return

        if deal.get("seller_id") != user_id:
            await message.answer("❌ This deal does not belong to you as seller.")
            return

        if deal.get("status") != "DEPOSITED":
            await message.answer(
                f"❌ Deal `{deal_id}` cannot be marked delivered (status: `{deal.get('status')}`).",
                parse_mode="Markdown"
            )
            return

        await DealCRUD.mark_delivered(db, deal_id)
        await message.answer(
            f"✅ *Delivery Confirmed*\n\n"
            f"Deal: `{deal_id}`\n"
            f"Status: DELIVERED\n\n"
            f"Waiting for buyer to confirm receipt...",
            reply_markup=MainMenuKeyboard.get_main_menu(),
            parse_mode="Markdown"
        )

    except Exception as e:
        logger.error(f"Error in delivered command: {e}")
        await message.answer("❌ An error occurred. Please try again.")


@router.message(Command("complete_deal"))
async def cmd_complete_deal(message: Message, db: AsyncIOMotorDatabase):
    """Handle /complete_deal command. Usage: /complete_deal <deal_id>"""
    try:
        args = message.text.split()
        user_id = message.from_user.id

        if len(args) < 2:
            deals = await DealCRUD.get_user_deals(db, user_id, "buyer")
            delivered = [d for d in deals if d.get("status") == "DELIVERED"]

            if not delivered:
                await message.answer(
                    "❌ No delivered deals ready to complete.\n\n"
                    "Usage: `/complete_deal DEAL_XXXXXXXX`",
                    parse_mode="Markdown"
                )
                return

            deals_list = "\n".join(
                f"• `{d['deal_id']}` — {d['amount']} {d['currency']} — {d['description'][:40]}"
                for d in delivered
            )
            await message.answer(
                f"🎉 *Deals Awaiting Your Confirmation:*\n\n{deals_list}\n\n"
                f"Reply with: `/complete_deal DEAL_XXXXXXXX`",
                parse_mode="Markdown"
            )
            return

        deal_id = args[1].upper()
        deal = await DealCRUD.get_deal(db, deal_id)

        if not deal:
            await message.answer(f"❌ Deal `{deal_id}` not found.", parse_mode="Markdown")
            return

        if deal.get("buyer_id") != user_id:
            await message.answer("❌ This deal does not belong to you as buyer.")
            return

        if deal.get("status") != "DELIVERED":
            await message.answer(
                f"❌ Deal `{deal_id}` is not in DELIVERED status (current: `{deal.get('status')}`).",
                parse_mode="Markdown"
            )
            return

        if await DealCRUD.complete_deal(db, deal_id):
            # Update stats using $inc for atomicity
            if deal.get("seller_id"):
                await db.users.update_one(
                    {"_id": deal["seller_id"]},
                    {"$inc": {"stats.completed_deals": 1, "stats.total_deals": 1}}
                )
            await db.users.update_one(
                {"_id": user_id},
                {"$inc": {"stats.completed_deals": 1, "stats.total_deals": 1}}
            )

            await message.answer(
                f"🎉 *Deal Completed!*\n\n"
                f"Deal: `{deal_id}`\n"
                f"Amount: {deal.get('amount')} {deal.get('currency')}\n"
                f"Status: COMPLETED\n\n"
                f"✅ Funds released to seller\n\n"
                f"Thank you for using Escrow Bot!",
                reply_markup=MainMenuKeyboard.get_main_menu(),
                parse_mode="Markdown"
            )
        else:
            await message.answer("❌ Failed to complete deal.")

    except Exception as e:
        logger.error(f"Error in complete deal command: {e}")
        await message.answer("❌ An error occurred. Please try again.")


@router.callback_query(F.data.startswith("delivered_"))
async def callback_delivered(callback: CallbackQuery, db: AsyncIOMotorDatabase):
    """Handle delivered callback."""
    try:
        deal_id = callback.data[len("delivered_"):]

        if await DealCRUD.mark_delivered(db, deal_id):
            deal = await DealCRUD.get_deal(db, deal_id)

            await callback.message.edit_text(
                f"✅ *Delivery Confirmed*\n\n{Formatters.format_deal_info(deal)}\n\n"
                f"⏳ Waiting for buyer to confirm receipt...",
                reply_markup=DealActionKeyboard.get_deal_actions(deal_id, "DELIVERED"),
                parse_mode="Markdown"
            )

        await callback.answer()

    except Exception as e:
        logger.error(f"Error in delivered callback: {e}")
        await callback.answer("❌ An error occurred")


@router.callback_query(F.data.startswith("complete_"))
async def callback_complete(callback: CallbackQuery, db: AsyncIOMotorDatabase):
    """Handle complete callback."""
    try:
        deal_id = callback.data[len("complete_"):]
        deal = await DealCRUD.get_deal(db, deal_id)

        if not deal:
            await callback.answer("❌ Deal not found", show_alert=True)
            return

        if await DealCRUD.complete_deal(db, deal_id):
            if deal.get("seller_id"):
                await db.users.update_one(
                    {"_id": deal["seller_id"]},
                    {"$inc": {"stats.completed_deals": 1, "stats.total_deals": 1}}
                )
            await db.users.update_one(
                {"_id": deal["buyer_id"]},
                {"$inc": {"stats.completed_deals": 1, "stats.total_deals": 1}}
            )

            await callback.message.edit_text(
                f"🎉 *Deal Completed!*\n\n"
                f"{Formatters.format_deal_info(deal)}\n\n"
                f"✅ Funds released to seller",
                reply_markup=MainMenuKeyboard.get_main_menu(),
                parse_mode="Markdown"
            )

        await callback.answer()

    except Exception as e:
        logger.error(f"Error in complete callback: {e}")
        await callback.answer("❌ An error occurred")
