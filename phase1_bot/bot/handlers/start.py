"""
Start Command Handler
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from motor.motor_asyncio import AsyncIOMotorDatabase
from database.crud import UserCRUD
from bot.keyboards import MainMenuKeyboard
from bot.utils.formatters import Formatters
from loguru import logger


router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message, db: AsyncIOMotorDatabase):
    """Handle /start command."""
    user = message.from_user
    
    try:
        # Check if user exists
        user_doc = await UserCRUD.get_user(db, user.id)
        
        if not user_doc:
            # Create new user
            await UserCRUD.create_user(
                db,
                user.id,
                user.username or f"user_{user.id}",
                user.first_name,
                user.last_name
            )
            welcome_msg = f"👋 Welcome {user.first_name}! I'm your secure cryptocurrency escrow bot.\n\n"
        else:
            welcome_msg = f"👋 Welcome back {user.first_name}!\n\n"
        
        welcome_msg += f"""🔒 *Crypto Escrow Bot*

*Supported Currencies:* BTC, USDT, LTC

*What can I do?*
• Create secure escrow deals
• Track payments
• Manage disputes
• Release funds safely

*Get started:*
1️⃣ Register as buyer or seller
2️⃣ Create an escrow deal
3️⃣ Complete transactions safely

*Commands:*
/seller - Register as seller
/buyer - Register as buyer
/escrow - Create escrow deal
/mydeals - View your deals
/help - Show help

Let's get started! 👇
"""
        
        await message.answer(
            welcome_msg,
            reply_markup=MainMenuKeyboard.get_main_menu(),
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logger.error(f"Error in start command: {e}")
        await message.answer("❌ An error occurred. Please try again.")


@router.callback_query(F.data == "help")
async def callback_help(callback: CallbackQuery):
    """Handle help button."""
    await callback.message.edit_text(
        Formatters.format_help_message(),
        reply_markup=MainMenuKeyboard.get_main_menu(),
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(F.data == "back_to_menu")
async def callback_back_to_menu(callback: CallbackQuery, state: FSMContext):
    """Handle back to menu button."""
    await state.clear()
    await callback.message.edit_text(
        "📋 *Main Menu*\n\nSelect an action:",
        reply_markup=MainMenuKeyboard.get_main_menu(),
        parse_mode="Markdown"
    )
    await callback.answer()


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    """Cancel any active FSM state."""
    current = await state.get_state()
    if current is not None:
        await state.clear()
        await message.answer(
            "✅ Cancelled.",
            reply_markup=MainMenuKeyboard.get_main_menu()
        )
    else:
        await message.answer(
            "ℹ️ Nothing to cancel.",
            reply_markup=MainMenuKeyboard.get_main_menu()
        )


@router.callback_query(F.data == "cancel")
async def callback_cancel(callback: CallbackQuery, state: FSMContext):
    """Handle cancel button — clear FSM and return to menu."""
    await state.clear()
    await callback.message.edit_text(
        "✅ Cancelled.\n\n📋 *Main Menu*\n\nSelect an action:",
        reply_markup=MainMenuKeyboard.get_main_menu(),
        parse_mode="Markdown"
    )
    await callback.answer()
