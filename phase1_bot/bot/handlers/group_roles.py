"""
Group Role Declaration — /seller <ADDRESS>, /buyer <ADDRESS>, /reset
All commands work inside the escrow group only.
"""

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message
from loguru import logger
from motor.motor_asyncio import AsyncIOMotorDatabase

from bot.utils.formatters import format_role_declaration, format_transaction_summary
from bot.utils.validators import detect_currency_from_address
from config.settings import settings
from database.crud import DealCRUD

router = Router()

# Map detected currency → operator escrow wallet
_ESCROW_ADDRESSES = {
    "BTC": settings.escrow_btc_address,
    "ETH": settings.escrow_eth_address,
    "USDT": settings.escrow_usdt_address,
    "LTC": settings.escrow_ltc_address,
}

_CURRENCY_LABELS = {
    "BTC": "Bitcoin (BTC)",
    "ETH": "Ethereum (ETH)",
    "USDT": "Tether TRC20 (USDT)",
    "LTC": "Litecoin (LTC)",
}

_SUPPORTED_FORMATS = (
    "Supported address formats:\n"
    "• Bitcoin: starts with `1`, `3`, or `bc1`\n"
    "• Ethereum: starts with `0x` (42 chars)\n"
    "• Litecoin: starts with `L` or `M`\n"
    "• USDT/TRC20: starts with `T` (34 chars)"
)


def _is_group(message: Message) -> bool:
    return message.chat.type in ("group", "supergroup")


@router.message(Command("seller"))
async def cmd_seller(message: Message, db: AsyncIOMotorDatabase):
    """Seller declares role + wallet address in the group."""
    if not _is_group(message):
        await message.reply("ℹ️ The `/seller` command can only be used inside the escrow group.")
        return

    args = message.text.split(maxsplit=1)
    if len(args) < 2 or not args[1].strip():
        await message.reply(
            "Usage: `/seller <your wallet address>`\n\n" + _SUPPORTED_FORMATS,
            parse_mode="Markdown",
        )
        return

    address = args[1].strip()
    currency = detect_currency_from_address(address)
    if not currency:
        await message.reply(
            "❌ *Unrecognised wallet address.*\n\n" + _SUPPORTED_FORMATS,
            parse_mode="Markdown",
        )
        return

    deal = await DealCRUD.get_deal_by_group_id(db, message.chat.id)
    if not deal:
        await message.reply("❌ No escrow deal found for this group.")
        return

    if deal.get("status") not in ("SETUP",):
        await message.reply(
            "❌ Roles are already locked. "
            "Type `/reset` first if you need to start over."
        )
        return

    if deal.get("seller_id"):
        await message.reply(
            f"⚠️ Seller is already set to @{deal.get('seller_username')}.\n"
            "Type `/reset` to clear all roles and start again."
        )
        return

    user = message.from_user
    username = user.username or f"user_{user.id}"

    await DealCRUD.update_seller_in_deal(
        db,
        deal_id=deal["deal_id"],
        seller_id=user.id,
        seller_username=username,
        seller_address=address,
        currency=currency,
    )

    declaration = format_role_declaration(
        role="seller",
        username=username,
        user_id=user.id,
        address=address,
        currency=_CURRENCY_LABELS.get(currency, currency),
    )
    await message.reply(
        declaration + "\n\n"
        f"✅ Seller confirmed as *{currency}*.\n\n"
        f"Buyer, please type:\n`/buyer <your {currency} wallet address>`",
        parse_mode="Markdown",
    )
    logger.info(f"Seller {user.id} set in deal {deal['deal_id']} with {currency}")


@router.message(Command("buyer"))
async def cmd_buyer(message: Message, db: AsyncIOMotorDatabase):
    """Buyer declares role + wallet address in the group."""
    if not _is_group(message):
        await message.reply("ℹ️ The `/buyer` command can only be used inside the escrow group.")
        return

    args = message.text.split(maxsplit=1)
    if len(args) < 2 or not args[1].strip():
        await message.reply(
            "Usage: `/buyer <your wallet address>`\n\n" + _SUPPORTED_FORMATS,
            parse_mode="Markdown",
        )
        return

    address = args[1].strip()
    currency = detect_currency_from_address(address)
    if not currency:
        await message.reply(
            "❌ *Unrecognised wallet address.*\n\n" + _SUPPORTED_FORMATS,
            parse_mode="Markdown",
        )
        return

    deal = await DealCRUD.get_deal_by_group_id(db, message.chat.id)
    if not deal:
        await message.reply("❌ No escrow deal found for this group.")
        return

    if deal.get("status") != "SETUP":
        await message.reply(
            "❌ Roles are already locked. "
            "Type `/reset` first if you need to start over."
        )
        return

    if not deal.get("seller_id"):
        await message.reply(
            "⚠️ Seller has not declared a role yet.\n"
            "Seller must type `/seller <address>` first."
        )
        return

    if deal.get("buyer_id"):
        await message.reply(
            f"⚠️ Buyer is already set to @{deal.get('buyer_username')}.\n"
            "Type `/reset` to clear all roles and start again."
        )
        return

    seller_currency = deal.get("currency")
    if currency != seller_currency:
        await message.reply(
            f"❌ *Currency mismatch!*\n\n"
            f"Seller is using *{seller_currency}* but your address is detected as *{currency}*.\n\n"
            f"Both parties must use the same currency.\n"
            f"Type `/reset` to clear roles and start over with a matching currency.",
            parse_mode="Markdown",
        )
        return

    escrow_address = _ESCROW_ADDRESSES.get(currency)
    if not escrow_address:
        await message.reply(
            f"❌ No escrow wallet configured for {currency}. Contact admin."
        )
        return

    user = message.from_user
    username = user.username or f"user_{user.id}"

    await DealCRUD.update_buyer_in_deal(
        db,
        deal_id=deal["deal_id"],
        buyer_id=user.id,
        buyer_username=username,
        buyer_address=address,
        escrow_address=escrow_address,
    )

    # Refresh deal to get all fields
    deal = await DealCRUD.get_deal(db, deal["deal_id"])

    buyer_declaration = format_role_declaration(
        role="buyer",
        username=username,
        user_id=user.id,
        address=address,
        currency=_CURRENCY_LABELS.get(currency, currency),
    )
    await message.reply(buyer_declaration, parse_mode="Markdown")
    await message.answer(format_transaction_summary(deal), parse_mode="Markdown")
    logger.info(f"Buyer {user.id} set in deal {deal['deal_id']} — summary posted")


@router.message(Command("reset"))
async def cmd_reset(message: Message, db: AsyncIOMotorDatabase):
    """Clear role declarations so both parties can re-declare."""
    if not _is_group(message):
        await message.reply("ℹ️ The `/reset` command can only be used inside the escrow group.")
        return

    deal = await DealCRUD.get_deal_by_group_id(db, message.chat.id)
    if not deal:
        await message.reply("❌ No escrow deal found for this group.")
        return

    if deal.get("status") != "SETUP":
        await message.reply(
            "❌ Cannot reset — the transaction summary has already been posted "
            "and the deposit is awaited. Contact `/contact` for admin help."
        )
        return

    await DealCRUD.reset_roles(db, deal["deal_id"])
    await message.reply(
        "🔄 *Roles have been reset.*\n\n"
        "Seller, please type `/seller <your wallet address>` to begin again.",
        parse_mode="Markdown",
    )
    logger.info(f"Roles reset for deal {deal['deal_id']}")
