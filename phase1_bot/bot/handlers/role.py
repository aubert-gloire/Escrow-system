"""
Role Selection Handler (Seller/Buyer)
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from motor.motor_asyncio import AsyncIOMotorDatabase
from database.crud import UserCRUD
from bot.keyboards import RoleKeyboard, MainMenuKeyboard
from bot.utils.validators import AddressValidator
from loguru import logger


router = Router()


class RoleStates(StatesGroup):
    """FSM states for role selection."""
    waiting_for_seller_currency = State()
    waiting_for_seller_address = State()


@router.message(Command("seller"))
async def cmd_seller(message: Message, state: FSMContext, db: AsyncIOMotorDatabase):
    """Handle /seller command."""
    try:
        user_id = message.from_user.id
        
        # Update user role
        await UserCRUD.update_user_role(db, user_id, "seller")
        
        # Ask for currency preference
        await message.answer(
            "🛡️ *Register as Seller*\n\nSelect your preferred currency:",
            reply_markup=RoleKeyboard.get_currency_selection(),
            parse_mode="Markdown"
        )
        
        await state.set_state(RoleStates.waiting_for_seller_currency)
        
    except Exception as e:
        logger.error(f"Error in seller command: {e}")
        await message.answer("❌ An error occurred. Please try again.")


@router.message(Command("buyer"))
async def cmd_buyer(message: Message, state: FSMContext, db: AsyncIOMotorDatabase):
    """Handle /buyer command."""
    try:
        user_id = message.from_user.id
        
        # Update user role
        await UserCRUD.update_user_role(db, user_id, "buyer")
        
        await message.answer(
            "🛒 *You're now registered as a Buyer*\n\n✅ You can now create escrow deals!\n\nUse /escrow to create a new deal.",
            reply_markup=MainMenuKeyboard.get_main_menu(),
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logger.error(f"Error in buyer command: {e}")
        await message.answer("❌ An error occurred. Please try again.")


@router.callback_query(RoleStates.waiting_for_seller_currency, F.data.startswith("currency_"))
async def callback_seller_currency(callback: CallbackQuery, state: FSMContext, db: AsyncIOMotorDatabase):
    """Handle seller currency selection."""
    try:
        currency = callback.data.split("_")[1]
        
        # Store in state
        await state.update_data(currency=currency)
        
        await callback.message.edit_text(
            f"📝 *Enter your {currency} receiving address:*\n\nExample:\n`1A1z7agoat91...`",
            parse_mode="Markdown"
        )
        
        await state.set_state(RoleStates.waiting_for_seller_address)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in seller currency callback: {e}")
        await callback.answer("❌ An error occurred")


@router.message(RoleStates.waiting_for_seller_address)
async def msg_seller_address(message: Message, state: FSMContext, db: AsyncIOMotorDatabase):
    """Handle seller address input."""
    try:
        address = message.text.strip()
        data = await state.get_data()
        currency = data.get("currency")
        user_id = message.from_user.id
        
        # Validate address
        is_valid, validation_msg = AddressValidator.validate_address(address, currency)
        
        if not is_valid:
            await message.answer(f"❌ {validation_msg}\n\nPlease try again:")
            return
        
        # Store address in database
        await UserCRUD.update_seller_address(db, user_id, currency, address)
        
        await message.answer(
            f"✅ *Seller Registered*\n\n{currency} Receiving Address:\n`{address}`\n\nYou can now receive escrow payments!",
            reply_markup=MainMenuKeyboard.get_main_menu(),
            parse_mode="Markdown"
        )
        
        await state.clear()
        
    except Exception as e:
        logger.error(f"Error in seller address message: {e}")
        await message.answer("❌ An error occurred. Please try again.")


@router.callback_query(F.data.startswith("role_"))
async def callback_role_selection(callback: CallbackQuery, state: FSMContext, db: AsyncIOMotorDatabase):
    """Handle role selection from menu."""
    try:
        role = callback.data.split("_")[1]
        user_id = callback.from_user.id
        
        if role == "seller":
            # Update role to seller
            await UserCRUD.update_user_role(db, user_id, "seller")
            
            # Ask for currency
            await callback.message.edit_text(
                "🛡️ *Register as Seller*\n\nSelect your preferred currency:",
                reply_markup=RoleKeyboard.get_currency_selection(),
                parse_mode="Markdown"
            )
            
            await state.set_state(RoleStates.waiting_for_seller_currency)
        
        elif role == "buyer":
            # Update role to buyer
            await UserCRUD.update_user_role(db, user_id, "buyer")
            
            await callback.message.edit_text(
                "🛒 *You're now registered as a Buyer*\n\n✅ You can now create escrow deals!\n\nUse /escrow to create a new deal.",
                reply_markup=MainMenuKeyboard.get_main_menu(),
                parse_mode="Markdown"
            )
        
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in role selection callback: {e}")
        await callback.answer("❌ An error occurred")
