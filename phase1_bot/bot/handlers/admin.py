"""Admin Handler"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from motor.motor_asyncio import AsyncIOMotorDatabase
from config.settings import settings
from database.crud import DealCRUD
from bot.keyboards import MainMenuKeyboard
from bot.utils.formatters import Formatters
from loguru import logger


router = Router()


class AdminStates(StatesGroup):
    """FSM states for admin commands."""
    waiting_for_confirm_deal_id = State()
    waiting_for_confirm_confirmations = State()
    waiting_for_resolve_deal_id = State()
    waiting_for_resolve_winner = State()


def is_admin(user_id: int) -> bool:
    """Check if user is admin."""
    return user_id in settings.admin_user_ids


@router.message(Command("admin"))
async def cmd_admin(message: Message):
    """Handle /admin command."""
    user_id = message.from_user.id

    if not is_admin(user_id):
        await message.answer("❌ Admin only command.")
        return

    await message.answer(
        "👨‍💼 *Admin Panel*\n\n"
        "Available commands:\n"
        "/verify_deposit - Verify deposit\n"
        "/resolve_dispute - Resolve dispute\n"
        "/help - Show help\n\n"
        "Status: ✅ Online",
        parse_mode="Markdown"
    )


@router.message(Command("verify_deposit"))
async def cmd_verify_deposit(message: Message, state: FSMContext, db: AsyncIOMotorDatabase):
    """Handle /verify_deposit command."""
    user_id = message.from_user.id

    if not is_admin(user_id):
        await message.answer("❌ Admin only command.")
        return

    args = message.text.split()

    if len(args) >= 3:
        deal_id = args[1].upper()
        try:
            confirmations = int(args[2])
        except ValueError:
            await message.answer("❌ Confirmations must be a number.")
            return
        await _do_verify_deposit(message, deal_id, confirmations, state, db)
    elif len(args) == 2:
        deal_id = args[1].upper()
        await state.update_data(deal_id=deal_id)
        await message.answer("Enter number of confirmations:")
        await state.set_state(AdminStates.waiting_for_confirm_confirmations)
    else:
        await message.answer("Enter deal ID to verify:")
        await state.set_state(AdminStates.waiting_for_confirm_deal_id)


@router.message(AdminStates.waiting_for_confirm_deal_id)
async def msg_admin_confirm_deal_id(message: Message, state: FSMContext):
    """Receive deal ID for deposit verification."""
    if not is_admin(message.from_user.id):
        await state.clear()
        return

    deal_id = message.text.strip().upper()
    await state.update_data(deal_id=deal_id)
    await message.answer(f"Deal: `{deal_id}`\n\nEnter number of confirmations:", parse_mode="Markdown")
    await state.set_state(AdminStates.waiting_for_confirm_confirmations)


@router.message(AdminStates.waiting_for_confirm_confirmations)
async def msg_admin_confirm_confirmations(message: Message, state: FSMContext, db: AsyncIOMotorDatabase):
    """Receive confirmation count and verify deposit."""
    if not is_admin(message.from_user.id):
        await state.clear()
        return

    try:
        confirmations = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Please enter a valid number:")
        return

    data = await state.get_data()
    deal_id = data.get("deal_id")
    await _do_verify_deposit(message, deal_id, confirmations, state, db)


async def _do_verify_deposit(message: Message, deal_id: str, confirmations: int, state: FSMContext, db: AsyncIOMotorDatabase = None):
    """Perform deposit verification."""
    try:
        if db is None:
            await message.answer("❌ Database unavailable.")
            await state.clear()
            return

        if await DealCRUD.confirm_deposit(db, deal_id, confirmations):
            await message.answer(
                f"✅ *Deposit Verified*\n\n"
                f"Deal: `{deal_id}`\n"
                f"Confirmations: {confirmations}\n"
                f"Status: DEPOSITED\n\n"
                f"Seller notified to proceed with delivery.",
                parse_mode="Markdown"
            )
        else:
            await message.answer(f"❌ Failed to verify deposit for `{deal_id}`. Check the deal ID.", parse_mode="Markdown")

        await state.clear()

    except Exception as e:
        logger.error(f"Error verifying deposit: {e}")
        await message.answer(f"❌ Error: {e}")
        await state.clear()


@router.message(Command("resolve_dispute"))
async def cmd_resolve_dispute(message: Message, state: FSMContext, db: AsyncIOMotorDatabase):
    """Handle /resolve_dispute command."""
    user_id = message.from_user.id

    if not is_admin(user_id):
        await message.answer("❌ Admin only command.")
        return

    args = message.text.split()

    if len(args) >= 3:
        deal_id = args[1].upper()
        winner = args[2].lower()
        await _do_resolve_dispute(message, deal_id, winner, state, db)
    elif len(args) == 2:
        deal_id = args[1].upper()
        await state.update_data(deal_id=deal_id)
        await message.answer("Enter winner (`buyer` or `seller`):", parse_mode="Markdown")
        await state.set_state(AdminStates.waiting_for_resolve_winner)
    else:
        await message.answer("Enter deal ID:")
        await state.set_state(AdminStates.waiting_for_resolve_deal_id)


@router.message(AdminStates.waiting_for_resolve_deal_id)
async def msg_admin_resolve_deal_id(message: Message, state: FSMContext):
    """Receive deal ID for dispute resolution."""
    if not is_admin(message.from_user.id):
        await state.clear()
        return

    deal_id = message.text.strip().upper()
    await state.update_data(deal_id=deal_id)
    await message.answer(f"Deal: `{deal_id}`\n\nEnter winner (`buyer` or `seller`):", parse_mode="Markdown")
    await state.set_state(AdminStates.waiting_for_resolve_winner)


@router.message(AdminStates.waiting_for_resolve_winner)
async def msg_admin_resolve_winner(message: Message, state: FSMContext, db: AsyncIOMotorDatabase):
    """Receive winner and resolve dispute."""
    if not is_admin(message.from_user.id):
        await state.clear()
        return

    winner = message.text.strip().lower()
    data = await state.get_data()
    deal_id = data.get("deal_id")
    await _do_resolve_dispute(message, deal_id, winner, state, db)


async def _do_resolve_dispute(message: Message, deal_id: str, winner: str, state: FSMContext, db: AsyncIOMotorDatabase = None):
    """Perform dispute resolution."""
    try:
        if winner not in ("buyer", "seller"):
            await message.answer("❌ Winner must be `buyer` or `seller`.", parse_mode="Markdown")
            return

        if db is None:
            await message.answer("❌ Database unavailable.")
            await state.clear()
            return

        if await DealCRUD.resolve_dispute(db, deal_id, winner):
            await message.answer(
                f"✅ *Dispute Resolved*\n\n"
                f"Deal: `{deal_id}`\n"
                f"Winner: {winner.upper()}\n"
                f"Status: COMPLETED\n\n"
                f"Funds released accordingly.",
                parse_mode="Markdown"
            )
        else:
            await message.answer(f"❌ Failed to resolve dispute for `{deal_id}`. Check the deal ID.", parse_mode="Markdown")

        await state.clear()

    except Exception as e:
        logger.error(f"Error resolving dispute: {e}")
        await message.answer(f"❌ Error: {e}")
        await state.clear()


@router.callback_query(F.data.startswith("resolve_"))
async def callback_resolve_dispute(callback: CallbackQuery, db: AsyncIOMotorDatabase):
    """Handle dispute resolution from inline keyboard (admin only)."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Admin only", show_alert=True)
        return

    try:
        parts = callback.data.split("_")
        # Format: resolve_buyer_<deal_id> or resolve_seller_<deal_id>
        if len(parts) < 3:
            await callback.answer("❌ Invalid callback data", show_alert=True)
            return

        winner = parts[1]
        deal_id = "_".join(parts[2:])

        if winner not in ("buyer", "seller"):
            await callback.answer("❌ Invalid winner", show_alert=True)
            return

        if await DealCRUD.resolve_dispute(db, deal_id, winner):
            await callback.message.edit_text(
                f"✅ *Dispute Resolved*\n\nDeal: `{deal_id}`\nWinner: {winner.upper()}",
                parse_mode="Markdown"
            )
        else:
            await callback.answer("❌ Failed to resolve dispute", show_alert=True)

        await callback.answer()

    except Exception as e:
        logger.error(f"Error in resolve dispute callback: {e}")
        await callback.answer("❌ An error occurred")
