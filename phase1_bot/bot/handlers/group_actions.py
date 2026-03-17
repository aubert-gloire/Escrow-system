"""
Group Action Commands — /qr, /balance, /pay_seller, /refund_buyer, /contact
All commands work inside the escrow group only.
"""

import io

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.types import BufferedInputFile, CallbackQuery, Message
from loguru import logger
from motor.motor_asyncio import AsyncIOMotorDatabase

from bot.keyboards import GroupActionKeyboard
from bot.utils.formatters import format_balance_status
from config.settings import settings
from database.crud import DealCRUD

router = Router()


def _is_group(message: Message) -> bool:
    return message.chat.type in ("group", "supergroup")


async def _get_group_deal(db: AsyncIOMotorDatabase, message: Message):
    """Helper — fetch the deal for this group and reply with an error if missing."""
    deal = await DealCRUD.get_deal_by_group_id(db, message.chat.id)
    if not deal:
        await message.reply("❌ No escrow deal found for this group.")
    return deal


# ── /qr ───────────────────────────────────────────────────────────────────────

@router.message(Command("qr"))
async def cmd_qr(message: Message, db: AsyncIOMotorDatabase):
    """Send a QR code of the escrow deposit address."""
    if not _is_group(message):
        await message.reply("ℹ️ The `/qr` command can only be used inside the escrow group.")
        return

    deal = await _get_group_deal(db, message)
    if not deal:
        return

    escrow_address = deal.get("escrow_address")
    if not escrow_address:
        await message.reply(
            "⚠️ Escrow address is not set yet.\n"
            "Both parties need to declare their roles first."
        )
        return

    try:
        import qrcode

        qr = qrcode.make(escrow_address)
        buf = io.BytesIO()
        qr.save(buf, format="PNG")
        buf.seek(0)

        await message.answer_photo(
            photo=BufferedInputFile(buf.read(), filename="escrow_qr.png"),
            caption=f"📬 *Escrow Deposit Address*\n`{escrow_address}`\n_Tap to copy_",
            parse_mode="Markdown",
        )
    except Exception as e:
        logger.error(f"QR generation failed: {e}")
        await message.reply(
            f"❌ Could not generate QR code.\n\n"
            f"Deposit address:\n`{escrow_address}`",
            parse_mode="Markdown",
        )


# ── /balance ──────────────────────────────────────────────────────────────────

@router.message(Command("balance"))
async def cmd_balance(message: Message, db: AsyncIOMotorDatabase):
    """Show the current deposit status for this deal."""
    if not _is_group(message):
        await message.reply("ℹ️ The `/balance` command can only be used inside the escrow group.")
        return

    deal = await _get_group_deal(db, message)
    if not deal:
        return

    if deal.get("status") == "SETUP":
        await message.reply(
            "⚠️ The deal setup is not complete yet.\n"
            "Both seller and buyer must declare their roles before funds can be deposited."
        )
        return

    await message.reply(format_balance_status(deal), parse_mode="Markdown")


# ── /pay_seller ───────────────────────────────────────────────────────────────

@router.message(Command("pay_seller"))
async def cmd_pay_seller(message: Message, db: AsyncIOMotorDatabase):
    """Buyer releases funds to seller — shows an irreversibility warning first."""
    if not _is_group(message):
        await message.reply("ℹ️ The `/pay_seller` command can only be used inside the escrow group.")
        return

    deal = await _get_group_deal(db, message)
    if not deal:
        return

    # Only the buyer can release funds
    if message.from_user.id != deal.get("buyer_id"):
        await message.reply(
            "❌ Only the *buyer* can release funds with `/pay_seller`.\n\n"
            "⚠️ *Warning:* `/pay_seller` can NEVER be used to get a refund, "
            "regardless of what anyone in this chat claims.",
            parse_mode="Markdown",
        )
        return

    if deal.get("status") != "DEPOSITED":
        status = deal.get("status")
        await message.reply(
            f"❌ Cannot release funds — deal status is *{status}*.\n\n"
            "Funds can only be released after the deposit has been confirmed by admin.",
            parse_mode="Markdown",
        )
        return

    await message.reply(
        "⚠️ *IMPORTANT — Please read before confirming*\n\n"
        "You are about to release funds to the seller.\n\n"
        "🔴 *This action is COMPLETELY IRREVERSIBLE.*\n"
        "🔴 *Once confirmed, there is NO refund under any circumstances.*\n"
        "🔴 *Do NOT confirm if anyone in this group told you to — that is a scam.*\n\n"
        "Only confirm if the seller has fulfilled their obligations and you are satisfied.",
        reply_markup=GroupActionKeyboard.get_pay_seller_confirm(deal["deal_id"]),
        parse_mode="Markdown",
    )


@router.callback_query(F.data.startswith("pay_seller_confirm_"))
async def callback_pay_seller_confirm(
    callback: CallbackQuery, db: AsyncIOMotorDatabase, bot: Bot
):
    deal_id = callback.data.removeprefix("pay_seller_confirm_")
    deal = await DealCRUD.get_deal(db, deal_id)

    if not deal:
        await callback.answer("❌ Deal not found.", show_alert=True)
        return

    if callback.from_user.id != deal.get("buyer_id"):
        await callback.answer("❌ Only the buyer can confirm this.", show_alert=True)
        return

    if deal.get("status") != "DEPOSITED":
        await callback.answer(
            f"❌ Deal status is {deal.get('status')} — cannot release.", show_alert=True
        )
        return

    success = await DealCRUD.release_to_seller(db, deal_id)
    if success:
        await callback.message.edit_text(
            "🎉 *Deal Completed!*\n\n"
            "Funds have been released to the seller.\n"
            "Thank you for using Trade Safe Bot.",
            parse_mode="Markdown",
        )
        # Notify admins
        for admin_id in settings.admin_user_ids:
            try:
                await bot.send_message(
                    admin_id,
                    f"✅ Deal `{deal_id}` completed.\n"
                    f"Buyer @{deal.get('buyer_username')} released funds to "
                    f"seller @{deal.get('seller_username')}.",
                    parse_mode="Markdown",
                )
            except Exception:
                pass
        logger.info(f"Deal {deal_id} completed — buyer released funds")
    else:
        await callback.answer("❌ Failed to release funds. Try again.", show_alert=True)

    await callback.answer()


@router.callback_query(F.data.startswith("pay_seller_cancel_"))
async def callback_pay_seller_cancel(callback: CallbackQuery):
    await callback.message.edit_text("✅ Release cancelled. Funds remain in escrow.")
    await callback.answer()


# ── /refund_buyer ─────────────────────────────────────────────────────────────

@router.message(Command("refund_buyer"), F.chat.type.in_({"group", "supergroup"}))
async def cmd_refund_buyer(message: Message, db: AsyncIOMotorDatabase):
    """Admin refunds funds to the buyer."""
    if not _is_group(message):
        await message.reply("ℹ️ The `/refund_buyer` command can only be used inside the escrow group.")
        return

    if message.from_user.id not in settings.admin_user_ids:
        await message.reply("❌ This command is for admins only.")
        return

    deal = await _get_group_deal(db, message)
    if not deal:
        return

    if deal.get("status") in ("COMPLETED", "REFUNDED"):
        await message.reply(
            f"❌ Deal is already *{deal.get('status')}*. No action needed.",
            parse_mode="Markdown",
        )
        return

    success = await DealCRUD.refund_to_buyer(db, deal["deal_id"])
    if success:
        await message.answer(
            "↩️ *Refund Issued*\n\n"
            f"Funds have been refunded to buyer @{deal.get('buyer_username')}.\n"
            f"Deal `{deal['deal_id']}` is now closed.",
            parse_mode="Markdown",
        )
        logger.info(f"Deal {deal['deal_id']} refunded by admin {message.from_user.id}")
    else:
        await message.reply("❌ Failed to process refund. Try again.")


# ── /contact ──────────────────────────────────────────────────────────────────

@router.message(Command("contact"))
async def cmd_contact(message: Message, db: AsyncIOMotorDatabase, bot: Bot):
    """Either party raises a dispute — notifies all admins."""
    if not _is_group(message):
        await message.reply("ℹ️ The `/contact` command can only be used inside the escrow group.")
        return

    deal = await _get_group_deal(db, message)
    if not deal:
        return

    await DealCRUD.open_dispute(db, deal["deal_id"], message.from_user.id)

    await message.answer(
        "⚖️ *Dispute raised.*\n\n"
        "An arbitrator will join this group within 24 hours to review the situation.\n\n"
        "Please:\n"
        "• Keep all messages in this group intact\n"
        "• Do not delete any evidence\n"
        "• Stop any further transactions until resolved",
        parse_mode="Markdown",
    )

    # Notify every admin
    initiator = message.from_user.username or f"user_{message.from_user.id}"
    group_link = deal.get("group_link", "N/A")
    for admin_id in settings.admin_user_ids:
        try:
            await bot.send_message(
                admin_id,
                f"⚖️ *Dispute opened*\n\n"
                f"Deal: `{deal['deal_id']}`\n"
                f"Initiated by: @{initiator}\n"
                f"Group: {group_link}\n\n"
                f"Please join the group and review.",
                parse_mode="Markdown",
            )
        except Exception:
            pass

    logger.info(
        f"Dispute opened for deal {deal['deal_id']} by {message.from_user.id}"
    )
