"""
My Deals Handler
"""

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.filters import Command
from motor.motor_asyncio import AsyncIOMotorDatabase
from database.crud import DealCRUD, UserCRUD
from bot.keyboards import MainMenuKeyboard, DealActionKeyboard
from bot.utils.formatters import Formatters
from loguru import logger


router = Router()


@router.message(Command("mydeals"))
async def cmd_mydeals(message: Message, db: AsyncIOMotorDatabase):
    """Handle /mydeals command."""
    try:
        user_id = message.from_user.id
        user = await UserCRUD.get_user(db, user_id)
        
        if not user:
            await message.answer("❌ Please use /start first.")
            return
        
        role = user.get("role")
        
        if not role:
            await message.answer("❌ Please register as buyer or seller first.\n\n/seller or /buyer")
            return
        
        # Get user's deals
        deals = await DealCRUD.get_user_deals(db, user_id, role)
        
        if not deals:
            await message.answer(
                f"📭 No {role} deals yet.\n\nUse /escrow to create a new deal.",
                reply_markup=MainMenuKeyboard.get_main_menu()
            )
            return
        
        # Format deals
        deals_text = "*Your Deals*\n\n"
        
        for deal in deals:
            status_emoji = {
                "CREATED": "📝",
                "AWAITING_DEPOSIT": "⏳",
                "DEPOSITED": "✅",
                "DELIVERED": "🚚",
                "COMPLETED": "🎉",
                "DISPUTED": "⚠️"
            }.get(deal.get("status"), "❓")
            
            deals_text += f"{status_emoji} `{deal.get('deal_id')}` - {deal.get('amount')} {deal.get('currency')}\n"
            deals_text += f"   {deal.get('description')}\n\n"
        
        await message.answer(
            deals_text,
            reply_markup=MainMenuKeyboard.get_main_menu(),
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logger.error(f"Error in mydeals command: {e}")
        await message.answer("❌ An error occurred. Please try again.")


@router.callback_query(F.data.startswith("view_deal_"))
async def callback_view_deal(callback: CallbackQuery, db: AsyncIOMotorDatabase):
    """Handle view deal callback."""
    try:
        deal_id = callback.data[len("view_deal_"):]

        deal = await DealCRUD.get_deal(db, deal_id)

        if not deal:
            await callback.answer("❌ Deal not found", show_alert=True)
            return

        deal_info = Formatters.format_deal_summary(deal)

        await callback.message.edit_text(
            deal_info,
            reply_markup=DealActionKeyboard.get_deal_actions(deal_id, deal.get("status")),
            parse_mode="Markdown"
        )

        await callback.answer()

    except Exception as e:
        logger.error(f"Error in view deal callback: {e}")
        await callback.answer("❌ An error occurred")


@router.callback_query(F.data == "my_deals")
async def callback_my_deals(callback: CallbackQuery, db: AsyncIOMotorDatabase):
    """Handle my deals callback."""
    try:
        user_id = callback.from_user.id
        user = await UserCRUD.get_user(db, user_id)
        
        if not user or not user.get("role"):
            await callback.answer("❌ Please register first", show_alert=True)
            return
        
        role = user.get("role")
        deals = await DealCRUD.get_user_deals(db, user_id, role)
        
        if not deals:
            await callback.message.edit_text(
                f"📭 No {role} deals yet.",
                reply_markup=MainMenuKeyboard.get_main_menu()
            )
            await callback.answer()
            return
        
        # Format deals
        deals_text = "*Your Deals*\n\n"
        
        for deal in deals:
            status_emoji = {
                "CREATED": "📝",
                "AWAITING_DEPOSIT": "⏳",
                "DEPOSITED": "✅",
                "DELIVERED": "🚚",
                "COMPLETED": "🎉",
                "DISPUTED": "⚠️"
            }.get(deal.get("status"), "❓")
            
            deals_text += f"{status_emoji} `{deal.get('deal_id')}` - {deal.get('amount')} {deal.get('currency')}\n"
            deals_text += f"   {deal.get('description')}\n\n"
        
        await callback.message.edit_text(
            deals_text,
            reply_markup=MainMenuKeyboard.get_main_menu(),
            parse_mode="Markdown"
        )
        
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in my deals callback: {e}")
        await callback.answer("❌ An error occurred")
