"""
Dispute Handler
"""

from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message
from motor.motor_asyncio import AsyncIOMotorDatabase
from database.crud import DealCRUD
from bot.keyboards import MainMenuKeyboard, DealActionKeyboard
from bot.utils.formatters import Formatters
from loguru import logger


router = Router()


class DisputeStates(StatesGroup):
    """FSM states for dispute."""
    waiting_for_reason = State()


@router.message(Command("dispute"))
async def cmd_dispute(message: Message, state: FSMContext, db: AsyncIOMotorDatabase):
    """Handle /dispute command."""
    try:
        user_id = message.from_user.id
        
        # Get user's delivered deals
        deals = await DealCRUD.get_user_deals(db, user_id, "buyer")
        delivered_deals = [d for d in deals if d.get("status") == "DELIVERED"]
        
        if not delivered_deals:
            await message.answer("❌ No delivered deals to dispute.")
            return
        
        # Mark first one for dispute
        deal = delivered_deals[0]
        await state.update_data(deal_id=deal.get("deal_id"))
        
        await message.answer(
            "⚠️ *Raise Dispute*\n\nPlease provide reason for the dispute:\n\n(Keep it brief, max 200 characters)",
            parse_mode="Markdown"
        )
        
        await state.set_state(DisputeStates.waiting_for_reason)
        
    except Exception as e:
        logger.error(f"Error in dispute command: {e}")
        await message.answer("❌ An error occurred. Please try again.")


@router.message(DisputeStates.waiting_for_reason)
async def msg_dispute_reason(message: Message, state: FSMContext, db: AsyncIOMotorDatabase):
    """Handle dispute reason input."""
    try:
        reason = message.text.strip()
        
        if len(reason) < 5:
            await message.answer("❌ Please provide more details (min 5 characters):")
            return
        
        if len(reason) > 200:
            await message.answer("❌ Reason too long (max 200 characters). Please try again:")
            return
        
        data = await state.get_data()
        deal_id = data.get("deal_id")
        user_id = message.from_user.id
        
        # Raise dispute
        if await DealCRUD.raise_dispute(db, deal_id, user_id, reason):
            await message.answer(
                f"✅ *Dispute Raised*\n\n"
                f"Deal: {deal_id}\n"
                f"Reason: {reason}\n\n"
                f"Admin team notified.\n"
                f"We'll investigate and contact you shortly.",
                reply_markup=MainMenuKeyboard.get_main_menu(),
                parse_mode="Markdown"
            )
        else:
            await message.answer("❌ Failed to raise dispute.")
        
        await state.clear()
        
    except Exception as e:
        logger.error(f"Error in dispute reason message: {e}")
        await message.answer("❌ An error occurred. Please try again.")


@router.callback_query(F.data.startswith("dispute_"))
async def callback_dispute(callback: CallbackQuery, state: FSMContext, db: AsyncIOMotorDatabase):
    """Handle dispute callback."""
    try:
        deal_id = callback.data[len("dispute_"):]

        deal = await DealCRUD.get_deal(db, deal_id)
        if not deal:
            await callback.answer("❌ Deal not found", show_alert=True)
            return

        await state.update_data(deal_id=deal_id)

        await callback.message.edit_text(
            f"⚠️ *Raise Dispute for Deal {deal_id}*\n\nPlease provide reason:\n\n(Max 200 characters)",
            parse_mode="Markdown"
        )

        await state.set_state(DisputeStates.waiting_for_reason)
        await callback.answer()

    except Exception as e:
        logger.error(f"Error in dispute callback: {e}")
        await callback.answer("❌ An error occurred")
