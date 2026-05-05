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

from bot.utils.blockchain_verifier import verify_transaction
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
    is_group = message.chat.type in ("group", "supergroup")

    # ── From group: deal_id auto-resolved from group_id ───────────────────────
    if is_group:
        deal = await DealCRUD.get_deal_by_group_id(db, message.chat.id)
        if not deal:
            await message.reply("❌ No escrow deal found for this group.")
            return
        deal_id = deal["deal_id"]
        if len(args) >= 2:
            tx_hash = args[1].strip()
            confirmations = int(args[2]) if len(args) >= 3 and args[2].isdigit() else 1
            await _do_verify_deposit(message, db, state, deal_id, tx_hash, confirmations, bot)
        else:
            # Hint: show the claimed TX hash if buyer already ran /paid
            claimed_tx = deal.get("payment_tx_claimed")
            if claimed_tx:
                await message.reply(
                    f"Buyer claimed TX:\n`{claimed_tx}`\n\n"
                    f"To confirm: `/verify_deposit {claimed_tx}`",
                    parse_mode="Markdown",
                )
            else:
                await message.reply(
                    f"Deal: `{deal_id}`\n\nUsage: `/verify_deposit <TX_HASH>`",
                    parse_mode="Markdown",
                )
        return

    # ── From DM: original behaviour ───────────────────────────────────────────
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
        deal = await DealCRUD.get_deal(db, deal_id)
        if not deal:
            await message.answer(
                f"❌ Deal `{deal_id}` not found.", parse_mode="Markdown"
            )
            await state.clear()
            return

        # ── On-chain verification ─────────────────────────────────────────────
        currency = deal.get("currency")
        escrow_address = deal.get("escrow_address")
        onchain = None
        verified_amount = None

        if currency and escrow_address:
            await message.answer("🔍 Checking blockchain…")
            onchain = await verify_transaction(
                currency=currency,
                tx_hash=tx_hash,
                expected_address=escrow_address,
                etherscan_api_key=settings.etherscan_api_key,
                blockcypher_token=settings.blockcypher_token,
            )

            if onchain["error"] and not onchain["found"]:
                # API failure — warn but allow manual approval
                await message.answer(
                    f"⚠️ *On-chain check failed:* {onchain['error']}\n\n"
                    "Proceeding with manual approval.",
                    parse_mode="Markdown",
                )
            elif onchain["found"] and not onchain["address_match"]:
                # TX exists but funds went elsewhere — block approval
                await message.answer(
                    f"🚨 *Address Mismatch — Approval Blocked*\n\n"
                    f"TX `{tx_hash}` was NOT sent to the escrow address.\n\n"
                    f"Expected: `{escrow_address}`\n\n"
                    "Deal NOT approved. Investigate before proceeding.",
                    parse_mode="Markdown",
                )
                await state.clear()
                return
            elif onchain["found"] and onchain["address_match"]:
                verified_amount = onchain["amount"]
                confirmations = onchain["confirmations"] or confirmations
                conf_line = f"Confirmations: {confirmations}"
                status_icon = "✅" if onchain["confirmed"] else "⏳ Unconfirmed"
                await message.answer(
                    f"🔗 *On-chain Result*\n\n"
                    f"Status: {status_icon}\n"
                    f"Amount received: `{verified_amount} {currency}`\n"
                    f"Address: ✅ Matches escrow\n"
                    f"{conf_line}",
                    parse_mode="Markdown",
                )

        # ── Approve in DB ─────────────────────────────────────────────────────
        success = await DealCRUD.confirm_deposit(
            db, deal_id, tx_hash, confirmations, verified_amount
        )
        if not success:
            await message.answer(
                f"❌ Could not update deal `{deal_id}`. "
                "It may already be past AWAITING_DEPOSIT status.",
                parse_mode="Markdown",
            )
            await state.clear()
            return

        amount_line = (
            f"Amount: `{verified_amount} {currency}`\n" if verified_amount else ""
        )
        await message.answer(
            f"✅ *Deposit Approved*\n\n"
            f"Deal: `{deal_id}`\n"
            f"TX: `{tx_hash}`\n"
            f"{amount_line}"
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
