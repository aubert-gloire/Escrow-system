"""
Deposit Confirmation Handler
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from motor.motor_asyncio import AsyncIOMotorDatabase
from database.crud import DealCRUD, TransactionCRUD
from bot.keyboards import MainMenuKeyboard, DealActionKeyboard
from bot.utils.formatters import Formatters
from bot.utils.validators import TxHashValidator
from loguru import logger


router = Router()


class DepositStates(StatesGroup):
    """FSM states for deposit confirmation."""
    waiting_for_deal_id = State()
    waiting_for_tx_hash = State()


@router.message(Command("confirm_deposit"))
async def cmd_confirm_deposit(message: Message, state: FSMContext):
    """Handle /confirm_deposit command."""
    try:
        args = message.text.split()

        if len(args) > 1:
            # Deal ID provided as argument — skip straight to tx hash
            deal_id = args[1]
            await state.update_data(deal_id=deal_id)
            await message.answer(
                f"📬 *Confirm Deposit for {deal_id}*\n\n"
                f"Enter the transaction hash:\n\nExample: `abc123def456...`",
                parse_mode="Markdown"
            )
            await state.set_state(DepositStates.waiting_for_tx_hash)
        else:
            await message.answer(
                "📬 *Confirm Deposit*\n\nEnter your Deal ID:\n\nExample: `DEAL_A1B2C3D4`",
                parse_mode="Markdown"
            )
            await state.set_state(DepositStates.waiting_for_deal_id)

    except Exception as e:
        logger.error(f"Error in confirm deposit command: {e}")
        await message.answer("❌ An error occurred. Please try again.")


@router.message(DepositStates.waiting_for_deal_id)
async def msg_deposit_deal_id(message: Message, state: FSMContext, db: AsyncIOMotorDatabase):
    """Handle deal ID input for deposit."""
    try:
        deal_id = message.text.strip().upper()

        deal = await DealCRUD.get_deal(db, deal_id)
        if not deal:
            await message.answer("❌ Deal not found. Please check the ID and try again:")
            return

        if deal.get("buyer_id") != message.from_user.id:
            await message.answer("❌ This deal does not belong to you.")
            await state.clear()
            return

        if deal.get("status") not in ("CREATED", "AWAITING_DEPOSIT"):
            await message.answer(
                f"❌ Deal {deal_id} is already in status `{deal.get('status')}` and cannot accept a deposit.",
                parse_mode="Markdown"
            )
            await state.clear()
            return

        await state.update_data(deal_id=deal_id)
        await message.answer(
            f"✅ Deal found: *{deal_id}*\n"
            f"Amount: {deal.get('amount')} {deal.get('currency')}\n\n"
            f"Now enter the transaction hash:",
            parse_mode="Markdown"
        )
        await state.set_state(DepositStates.waiting_for_tx_hash)

    except Exception as e:
        logger.error(f"Error in deposit deal id message: {e}")
        await message.answer("❌ An error occurred. Please try again.")


@router.message(DepositStates.waiting_for_tx_hash)
async def msg_confirm_deposit_tx(message: Message, state: FSMContext, db: AsyncIOMotorDatabase):
    """Handle deposit tx hash input."""
    try:
        tx_hash = message.text.strip()
        data = await state.get_data()
        deal_id = data.get("deal_id")

        if not deal_id:
            await message.answer("❌ Session expired. Please use /confirm_deposit again.")
            await state.clear()
            return

        # Fetch deal to get currency for validation
        deal = await DealCRUD.get_deal(db, deal_id)
        if not deal:
            await message.answer("❌ Deal not found.")
            await state.clear()
            return

        currency = deal.get("currency", "BTC")

        # Validate tx hash
        is_valid, validation_msg = TxHashValidator.validate_tx_hash(tx_hash, currency)
        if not is_valid:
            await message.answer(f"❌ {validation_msg}\n\nPlease try again:")
            return

        # Record the deposit in the database
        recorded = await DealCRUD.record_deposit(db, deal_id, tx_hash, deal.get("amount"))
        if not recorded:
            await message.answer("❌ Failed to record deposit. Please try again.")
            return

        # Create transaction record
        await TransactionCRUD.create_transaction(
            db,
            deal_id=deal_id,
            tx_type="deposit",
            amount=deal.get("amount"),
            currency=currency,
            tx_hash=tx_hash,
            to_address=deal.get("escrow_address")
        )

        await message.answer(
            f"⏳ *Deposit Recorded*\n\n"
            f"Deal: `{deal_id}`\n"
            f"Transaction hash: `{tx_hash}`\n\n"
            f"📊 Status: Awaiting admin verification\n"
            f"This may take 10 minutes to 1 hour depending on the network.\n\n"
            f"Admin will verify and notify you shortly.",
            reply_markup=MainMenuKeyboard.get_main_menu(),
            parse_mode="Markdown"
        )

        await state.clear()

    except Exception as e:
        logger.error(f"Error in confirm deposit message: {e}")
        await message.answer("❌ An error occurred. Please try again.")


@router.callback_query(F.data.startswith("confirm_deposit_"))
async def callback_confirm_deposit(callback: CallbackQuery, state: FSMContext):
    """Handle confirm deposit callback — pre-fills deal_id and asks for tx hash."""
    try:
        deal_id = callback.data[len("confirm_deposit_"):]

        await state.update_data(deal_id=deal_id)
        await callback.message.edit_text(
            f"📬 *Confirm Deposit for {deal_id}*\n\n"
            f"Enter the transaction hash:\n\nExample: `abc123def456...`",
            parse_mode="Markdown"
        )
        await state.set_state(DepositStates.waiting_for_tx_hash)
        await callback.answer()

    except Exception as e:
        logger.error(f"Error in confirm deposit callback: {e}")
        await callback.answer("❌ An error occurred")
