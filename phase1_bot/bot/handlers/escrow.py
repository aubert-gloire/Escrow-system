"""
Escrow Deal Creation Handler
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from motor.motor_asyncio import AsyncIOMotorDatabase
from database.crud import UserCRUD, DealCRUD
from config.settings import settings
from bot.keyboards import MainMenuKeyboard, GroupJoinKeyboard, RoleKeyboard
from bot.utils.formatters import Formatters
from bot.utils.validators import AmountValidator
from bot.utils.group_manager import GroupManager
from aiogram import Bot
import uuid
from loguru import logger


router = Router()


class EscrowStates(StatesGroup):
    """FSM states for escrow deal creation."""
    waiting_for_currency = State()
    waiting_for_amount = State()
    waiting_for_description = State()


# Mapping of currencies to escrow addresses
ESCROW_ADDRESSES = {
    "BTC": settings.escrow_btc_address,
    "USDT": settings.escrow_usdt_address,
    "ETH": settings.escrow_eth_address,
    "LTC": settings.escrow_ltc_address
}


@router.message(Command("escrow"))
async def cmd_escrow(message: Message, state: FSMContext, db: AsyncIOMotorDatabase):
    """Handle /escrow command."""
    try:
        user_id = message.from_user.id

        # Check if user exists and get their role
        user = await UserCRUD.get_user(db, user_id)

        if not user:
            await message.answer("❌ Please use /start first to register.")
            return

        await message.answer(
            "📋 *Create Escrow Deal*\n\nSelect the currency for this deal:",
            reply_markup=RoleKeyboard.get_currency_selection(),
            parse_mode="Markdown"
        )

        await state.set_state(EscrowStates.waiting_for_currency)

    except Exception as e:
        logger.error(f"Error in escrow command: {e}")
        await message.answer("❌ An error occurred. Please try again.")


@router.callback_query(EscrowStates.waiting_for_currency, F.data.startswith("currency_"))
async def callback_escrow_currency(callback: CallbackQuery, state: FSMContext):
    """Handle currency selection for escrow deal."""
    try:
        currency = callback.data.split("_")[1]
        await state.update_data(currency=currency)

        await callback.message.edit_text(
            f"📋 *Create Escrow Deal — {currency}*\n\nEnter the amount you want to escrow:\n\nExample: `0.5`",
            parse_mode="Markdown"
        )

        await state.set_state(EscrowStates.waiting_for_amount)
        await callback.answer()

    except Exception as e:
        logger.error(f"Error in escrow currency callback: {e}")
        await callback.answer("❌ An error occurred")


@router.message(EscrowStates.waiting_for_amount)
async def msg_escrow_amount(message: Message, state: FSMContext):
    """Handle escrow amount input."""
    try:
        amount_str = message.text.strip()

        # Validate amount
        is_valid, amount, validation_msg = AmountValidator.validate_amount(
            amount_str,
            settings.max_deal_amount
        )

        if not is_valid:
            await message.answer(f"❌ {validation_msg}\n\nPlease try again:")
            return

        await state.update_data(amount=amount)

        await message.answer(
            "📝 *Describe the deal:*\n\nWhat are you selling/buying?\n\nExample: `MacBook Pro 16GB RAM`\n\n(Max 200 characters)",
            parse_mode="Markdown"
        )

        await state.set_state(EscrowStates.waiting_for_description)

    except Exception as e:
        logger.error(f"Error in escrow amount message: {e}")
        await message.answer("❌ An error occurred. Please try again.")


@router.message(EscrowStates.waiting_for_description)
async def msg_escrow_description(message: Message, state: FSMContext, db: AsyncIOMotorDatabase, bot: Bot, user_client=None):
    """Handle escrow description input."""
    try:
        description = message.text.strip()
        
        if len(description) > 200:
            await message.answer("❌ Description too long (max 200 characters). Please try again:")
            return
        
        if len(description) < 3:
            await message.answer("❌ Description too short (min 3 characters). Please try again:")
            return
        
        # Get data
        data = await state.get_data()
        amount = data.get("amount")
        currency = data.get("currency", "BTC")
        user_id = message.from_user.id
        user = await UserCRUD.get_user(db, user_id)

        # Get escrow address
        escrow_address = ESCROW_ADDRESSES.get(currency)

        if not escrow_address:
            await message.answer(f"❌ No escrow address configured for {currency}. Contact admin.")
            await state.clear()
            return

        # Generate unique deal ID
        deal_id = f"DEAL_{uuid.uuid4().hex[:8].upper()}"

        # Create deal in database
        await DealCRUD.create_deal(
            db,
            deal_id=deal_id,
            buyer_id=user_id,
            buyer_username=user.get("username"),
            amount=amount,
            currency=currency,
            description=description,
            escrow_address=escrow_address
        )

        # Transition status to AWAITING_DEPOSIT immediately after creation
        await DealCRUD.update_deal_status(db, deal_id, "AWAITING_DEPOSIT")

        # Fetch the newly-created deal (used in both branches below)
        deal = await DealCRUD.get_deal(db, deal_id)

        # Attempt to create a group for this deal
        group_result = await GroupManager.create_group_for_deal(
            user_client,
            bot,
            deal_id,
            amount,
            currency,
            description
        )

        if group_result.get("success"):
            group_id = group_result.get("group_id")
            group_link = group_result.get("group_link")

            # Update deal with group info
            await DealCRUD.create_group(db, deal_id, group_id, group_link)
            # Refresh deal with group info
            deal = await DealCRUD.get_deal(db, deal_id)

            # Post full deal info + deposit address into the group
            await GroupManager.post_deal_info_to_group(bot, group_id, deal)

            # Post seller instructions into the group
            await GroupManager.send_group_message(
                bot, group_id,
                f"👋 *Seller:* Once you join this group, copy and send the command below to the bot in *private chat*:\n\n"
                f"```\n/join_deal {deal_id}\n```\n\n"
                f"⚠️ Send it to the bot in private — not here in the group.",
            )

            # Private message to buyer
            await message.answer(
                f"✅ *Escrow Deal Created!*\n\n"
                f"*Deal ID:* `{deal_id}`\n"
                f"*Amount:* {amount} {currency}\n"
                f"*Description:* {description}\n\n"
                f"📬 *Next Steps:*\n"
                f"1️⃣ Share the group link below with your seller\n"
                f"2️⃣ Seller joins and types `/join_deal {deal_id}` in the group\n"
                f"3️⃣ You'll be notified when seller joins\n"
                f"4️⃣ Send `{amount} {currency}` to the escrow address:\n\n"
                f"```\n{escrow_address}\n```\n"
                f"_tap to copy_\n\n"
                f"5️⃣ Then run `/confirm_deposit {deal_id}` and paste your TX hash",
                reply_markup=GroupJoinKeyboard.get_group_actions(group_link, deal_id),
                parse_mode="Markdown"
            )
        else:
            # Group creation not available — deal is still valid, show address directly
            await message.answer(
                f"✅ *Escrow Deal Created!*\n\n"
                f"*Deal ID:* `{deal_id}`\n"
                f"*Amount:* {amount} {currency}\n"
                f"*Description:* {description}\n\n"
                f"📬 *Send `{amount} {currency}` to:*\n\n"
                f"```\n{escrow_address}\n```\n"
                f"_tap to copy_\n\n"
                f"After sending, run:\n`/confirm_deposit {deal_id}`\nand paste your TX hash.\n\n"
                f"⚠️ Share deal ID `{deal_id}` with your seller so they can run `/join_deal {deal_id}`",
                reply_markup=MainMenuKeyboard.get_main_menu(),
                parse_mode="Markdown"
            )

        await state.clear()
        
    except Exception as e:
        logger.error(f"Error in escrow description message: {e}")
        await message.answer("❌ An error occurred. Please try again.")


@router.callback_query(F.data == "create_deal")
async def callback_create_deal(callback: CallbackQuery, state: FSMContext, db: AsyncIOMotorDatabase):
    """Handle create deal button."""
    try:
        user = await UserCRUD.get_user(db, callback.from_user.id)

        if not user:
            await callback.answer("❌ Please use /start first", show_alert=True)
            return

        await callback.message.edit_text(
            "📋 *Create Escrow Deal*\n\nSelect the currency for this deal:",
            reply_markup=RoleKeyboard.get_currency_selection(),
            parse_mode="Markdown"
        )

        await state.set_state(EscrowStates.waiting_for_currency)
        await callback.answer()

    except Exception as e:
        logger.error(f"Error in create deal callback: {e}")
        await callback.answer("❌ An error occurred")


@router.message(Command("join_deal"))
async def cmd_join_deal(message: Message, db: AsyncIOMotorDatabase, bot: Bot):
    """Seller uses this to formally join a deal. Usage: /join_deal DEAL_XXXXXXXX"""
    try:
        args = message.text.split()
        if len(args) < 2:
            await message.answer(
                "Usage: `/join_deal DEAL_XXXXXXXX`\n\nThe deal ID is shared by the buyer.",
                parse_mode="Markdown"
            )
            return

        deal_id = args[1].strip().upper()
        user_id = message.from_user.id
        user = await UserCRUD.get_user(db, user_id)

        if not user:
            await message.answer("❌ Please use /start first to register.")
            return

        deal = await DealCRUD.get_deal(db, deal_id)

        if not deal:
            await message.answer(f"❌ Deal `{deal_id}` not found.", parse_mode="Markdown")
            return

        if deal.get("buyer_id") == user_id:
            await message.answer("❌ You created this deal — you're already the buyer.")
            return

        if deal.get("seller_id"):
            if deal.get("seller_id") == user_id:
                await message.answer(f"✅ You're already joined as seller on deal `{deal_id}`.", parse_mode="Markdown")
            else:
                await message.answer("❌ This deal already has a seller.")
            return

        if deal.get("status") not in ("AWAITING_DEPOSIT", "CREATED"):
            await message.answer(
                f"❌ Deal `{deal_id}` is in status `{deal.get('status')}` and cannot be joined.",
                parse_mode="Markdown"
            )
            return

        # Get seller's address for this currency (if registered)
        currency = deal.get("currency", "BTC")
        seller_address = user.get("seller_addresses", {}).get(currency, "")

        # If seller has no address registered for this currency, ask for it
        if not seller_address:
            await message.answer(
                f"✅ *Joining Deal `{deal_id}` as Seller*\n\n"
                f"*Amount:* {deal.get('amount')} {currency}\n\n"
                f"📝 You don't have a {currency} receiving address registered.\n"
                f"Please enter your {currency} address now so you can receive payment when the deal completes:",
                parse_mode="Markdown"
            )
            # Store deal_id in FSM for address collection
            from aiogram.fsm.context import FSMContext
            # We still link seller to deal now (address can be updated later)
            pass

        # Link seller to deal
        await DealCRUD.update_seller_info(
            db,
            deal_id,
            seller_id=user_id,
            seller_username=user.get("username", str(user_id)),
            seller_address=seller_address
        )

        username = user.get("username", str(user_id))

        confirm_text = (
            f"✅ *You've joined Deal `{deal_id}` as Seller!*\n\n"
            f"*Amount:* {deal.get('amount')} {currency}\n"
            f"*Description:* {deal.get('description')}\n\n"
            f"⏳ Waiting for buyer to deposit funds.\n"
            f"You'll be notified once the deposit is confirmed.\n\n"
            f"When goods/service are delivered, run:\n`/delivered {deal_id}`"
        )
        if not seller_address:
            confirm_text += (
                f"\n\n⚠️ *Action needed:* Register your {currency} payout address with:\n"
                f"`/seller` → select {currency} → paste your address"
            )

        # Only send confirm if we didn't already send the address prompt above
        if seller_address:
            await message.answer(confirm_text, parse_mode="Markdown")
        else:
            await message.answer(confirm_text, parse_mode="Markdown")

        # Notify buyer
        try:
            await bot.send_message(
                chat_id=deal.get("buyer_id"),
                text=f"🎉 *Seller Joined!*\n\n"
                     f"@{username} has joined deal `{deal_id}` as seller.\n\n"
                     f"📬 *Now send your deposit:*\n"
                     f"Send `{deal.get('amount')} {currency}` to:\n\n"
                     f"```\n{deal.get('escrow_address')}\n```\n"
                     f"_tap to copy_\n\n"
                     f"After sending, run:\n`/confirm_deposit {deal_id}`\nand paste your TX hash.",
                parse_mode="Markdown"
            )
        except Exception:
            pass  # Buyer may have blocked the bot

        # Post update to group if one exists
        if deal.get("group_id"):
            try:
                await GroupManager.send_group_message(
                    bot,
                    deal.get("group_id"),
                    f"✅ *Seller @{username} has joined the deal!*\n\n"
                    f"*Buyer:* Please deposit `{deal.get('amount')} {currency}` to:\n\n"
                    f"```\n{deal.get('escrow_address')}\n```\n"
                    f"_tap to copy_\n\n"
                    f"Then run `/confirm_deposit {deal_id}` in the bot.",
                )
            except Exception:
                pass

        logger.info(f"Seller {user_id} joined deal {deal_id}")

    except Exception as e:
        logger.error(f"Error in join_deal command: {e}")
        await message.answer("❌ An error occurred. Please try again.")
