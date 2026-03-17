"""
Start Command Handler — /start, info callbacks, back to menu.
"""

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from loguru import logger
from motor.motor_asyncio import AsyncIOMotorDatabase

from bot.keyboards import MainMenuKeyboard
from bot.utils.formatters import (
    INSTRUCTIONS_TEXT,
    TERMS_TEXT,
    WHAT_IS_ESCROW_TEXT,
    format_welcome_dm,
)
from database.crud import DealCRUD, UserCRUD

router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message, db: AsyncIOMotorDatabase):
    user = message.from_user
    username = user.username or f"user_{user.id}"

    try:
        if not await UserCRUD.get_user(db, user.id):
            await UserCRUD.create_user(db, user.id, username, user.first_name, user.last_name)

        stats = await DealCRUD.get_stats(db)
        await message.answer(
            format_welcome_dm(stats),
            reply_markup=MainMenuKeyboard.get_main_menu(),
            parse_mode="Markdown",
        )
    except Exception as e:
        logger.error(f"Error in /start: {e}")
        await message.answer("❌ An error occurred. Please try again.")


@router.callback_query(F.data == "what_is_escrow")
async def callback_what_is_escrow(callback: CallbackQuery):
    await callback.message.answer(
        WHAT_IS_ESCROW_TEXT,
        reply_markup=MainMenuKeyboard.get_back_to_menu(),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(F.data == "instructions")
async def callback_instructions(callback: CallbackQuery):
    await callback.message.answer(
        INSTRUCTIONS_TEXT,
        reply_markup=MainMenuKeyboard.get_back_to_menu(),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(F.data == "terms")
async def callback_terms(callback: CallbackQuery):
    await callback.message.answer(
        TERMS_TEXT,
        reply_markup=MainMenuKeyboard.get_back_to_menu(),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(F.data == "back_to_menu")
async def callback_back_to_menu(callback: CallbackQuery, state: FSMContext, db: AsyncIOMotorDatabase):
    await state.clear()
    stats = await DealCRUD.get_stats(db)
    await callback.message.answer(
        format_welcome_dm(stats),
        reply_markup=MainMenuKeyboard.get_main_menu(),
        parse_mode="Markdown",
    )
    await callback.answer()
