"""
Admin Handler — /admin, /verify_deposit, /refund_buyer (DM fallback)
"""

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message
from loguru import logger
from motor.motor_asyncio import AsyncIOMotorDatabase

from bot.utils.formatters import format_deposit_verified
from config.settings import settings
from database.crud import DealCRUD

router = Router()


class AdminStates(StatesGroup):
    waiting_for_deal_id = State()
    waiting_for_tx_hash = State()
    waiting_for_refund_deal_id = State()


def _is_admin(user_id: int) -> bool:
    return user_id in settings.admin_user_ids


# ── /admin ────────────────────────────────────────────────────────────────────

@router.message(Command("admin"))
async def cmd_admin(message: Message):
    if not _is_admin(message.from_user.id):
        await message.answer("❌ Admin only command.")
        return

    await message.answer(
        "👨‍💼 *Admin Panel*\n\n"
        "Commands:\n"
        "`/verify_deposit <DEAL_ID> <TX_HASH>` — confirm a deposit\n"
        "`/refund_buyer <DEAL_ID>` — refund buyer (also works from the group)\n\n"
        "Status: ✅ Online",
        parse_mode="Markdown",
    )


# ── /verify_deposit ───────────────────────────────────────────────────────────

@router.message(Command("verify_deposit"))
async def cmd_verify_deposit(message: Message, state: FSMContext, db: AsyncIOMotorDatabase, bot: Bot):
    if not _is_admin(message.from_user.id):
        await message.answer("❌ Admin only command.")
        return

    args = message.text.split()

    if len(args) >= 3:
        deal_id = args[1].upper()
        tx_hash = args[2]
        confirmations = int(args[3]) if len(args) >= 4 and args[3].isdigit() else 1
        await _do_verify_deposit(message, db, state, deal_id, tx_hash, confirmations, bot)
    elif len(args) == 2:
        deal_id = args[1].upper()
        await state.update_data(deal_id=deal_id)
        await message.answer(
            f"Deal: `{deal_id}`\n\nEnter the deposit TX hash:",
            parse_mode="Markdown",
        )
        await state.set_state(AdminStates.waiting_for_tx_hash)
    else:
        await message.answer("Enter the deal ID to verify:")
        await state.set_state(AdminStates.waiting_for_deal_id)


@router.message(AdminStates.waiting_for_deal_id)
async def msg_admin_deal_id(message: Message, state: FSMContext):
    if not _is_admin(message.from_user.id):
        await state.clear()
        return
    deal_id = message.text.strip().upper()
    await state.update_data(deal_id=deal_id)
    await message.answer(
        f"Deal: `{deal_id}`\n\nEnter the deposit TX hash:",
        parse_mode="Markdown",
    )
    await state.set_state(AdminStates.waiting_for_tx_hash)


@router.message(AdminStates.waiting_for_tx_hash)
async def msg_admin_tx_hash(message: Message, state: FSMContext, db: AsyncIOMotorDatabase, bot: Bot):
    if not _is_admin(message.from_user.id):
        await state.clear()
        return
    tx_hash = message.text.strip()
    data = await state.get_data()
    deal_id = data.get("deal_id")
    await _do_verify_deposit(message, db, state, deal_id, tx_hash, confirmations=1, bot=bot)


async def _do_verify_deposit(
    message: Message,
    db: AsyncIOMotorDatabase,
    state: FSMContext,
    deal_id: str,
    tx_hash: str,
    confirmations: int,
    bot: Bot = None,
):
    try:
        success = await DealCRUD.confirm_deposit(db, deal_id, tx_hash, confirmations)
        if not success:
            await message.answer(
                f"❌ Could not verify deposit for `{deal_id}`. Check the deal ID.",
                parse_mode="Markdown",
            )
            await state.clear()
            return

        await message.answer(
            f"✅ *Deposit Verified*\n\n"
            f"Deal: `{deal_id}`\n"
            f"TX: `{tx_hash}`\n"
            f"Confirmations: {confirmations}\n"
            f"Status: DEPOSITED",
            parse_mode="Markdown",
        )

        # Notify the group
        if bot:
            deal = await DealCRUD.get_deal(db, deal_id)
            if deal and deal.get("group_id"):
                try:
                    await bot.send_message(
                        chat_id=deal["group_id"],
                        text=format_deposit_verified(deal),
                        parse_mode="Markdown",
                    )
                except Exception as e:
                    logger.warning(f"Could not notify group for deal {deal_id}: {e}")

        logger.info(f"Deposit verified — deal {deal_id} by admin {message.from_user.id}")
        await state.clear()

    except Exception as e:
        logger.error(f"Error verifying deposit: {e}")
        await message.answer(f"❌ Error: {e}")
        await state.clear()


# ── /refund_buyer (admin DM fallback) ─────────────────────────────────────────

@router.message(Command("refund_buyer"), F.chat.type == "private")
async def cmd_refund_buyer_dm(message: Message, state: FSMContext, db: AsyncIOMotorDatabase):
    """Admin issues a refund from DM by providing the deal ID."""
    if not _is_admin(message.from_user.id):
        await message.answer("❌ Admin only command.")
        return

    args = message.text.split()
    if len(args) >= 2:
        deal_id = args[1].upper()
        await _do_refund(message, db, state, deal_id)
    else:
        await message.answer("Enter the deal ID to refund:")
        await state.set_state(AdminStates.waiting_for_refund_deal_id)


@router.message(AdminStates.waiting_for_refund_deal_id)
async def msg_admin_refund_deal_id(message: Message, state: FSMContext, db: AsyncIOMotorDatabase):
    if not _is_admin(message.from_user.id):
        await state.clear()
        return
    deal_id = message.text.strip().upper()
    await _do_refund(message, db, state, deal_id)


async def _do_refund(
    message: Message,
    db: AsyncIOMotorDatabase,
    state: FSMContext,
    deal_id: str,
):
    try:
        deal = await DealCRUD.get_deal(db, deal_id)
        if not deal:
            await message.answer(f"❌ Deal `{deal_id}` not found.", parse_mode="Markdown")
            await state.clear()
            return

        if deal.get("status") in ("COMPLETED", "REFUNDED"):
            await message.answer(
                f"❌ Deal `{deal_id}` is already *{deal.get('status')}*.",
                parse_mode="Markdown",
            )
            await state.clear()
            return

        if await DealCRUD.refund_to_buyer(db, deal_id):
            await message.answer(
                f"↩️ *Refund Issued*\n\n"
                f"Deal `{deal_id}` — funds refunded to buyer @{deal.get('buyer_username')}.",
                parse_mode="Markdown",
            )
            logger.info(f"Deal {deal_id} refunded by admin {message.from_user.id} via DM")
        else:
            await message.answer(f"❌ Failed to refund `{deal_id}`.", parse_mode="Markdown")

        await state.clear()

    except Exception as e:
        logger.error(f"Error in refund: {e}")
        await message.answer(f"❌ Error: {e}")
        await state.clear()
