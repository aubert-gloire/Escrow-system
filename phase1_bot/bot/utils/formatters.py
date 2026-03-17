"""
Message formatting utilities for Trade Safe Bot.
"""

from datetime import datetime
from typing import Dict, Any


# ── Stats base offsets (added to real DB counts for display) ──────────────────
STATS_BASE_COMPLETED = 1_247
STATS_BASE_DISPUTES  = 94

# ── Static info placeholders ───────────────────────────────────────────────────
# TODO: Replace these with your real content before going live.

WHAT_IS_ESCROW_TEXT = (
    "🔒 *What is Escrow?*\n\n"
    "Escrow is a financial arrangement where a trusted third party holds "
    "and regulates the transfer of funds between two parties in a transaction. "
    "The funds are held securely until both parties fulfil their obligations.\n\n"
    "_[Placeholder — update with your own description.]_"
)

INSTRUCTIONS_TEXT = (
    "📋 *How to Use Trade Safe Bot*\n\n"
    "1️⃣ Click *Create Escrow Group* — the bot creates a private group for your deal.\n"
    "2️⃣ Share the invite link with the other party.\n"
    "3️⃣ *Seller* types `/seller <wallet address>` in the group.\n"
    "4️⃣ *Buyer* types `/buyer <wallet address>` in the group.\n"
    "5️⃣ The bot posts a transaction summary with the escrow deposit address.\n"
    "6️⃣ Buyer verifies the escrow address in our official channel, then sends funds.\n"
    "7️⃣ Once delivery is confirmed, buyer types `/pay_seller` to release funds.\n\n"
    "_[Placeholder — update with your own instructions.]_"
)

TERMS_TEXT = (
    "📜 *Terms & Conditions*\n\n"
    "By using Trade Safe Bot you agree to the following:\n\n"
    "• Funds sent to the escrow address are held until the deal is resolved.\n"
    "• `/pay_seller` is irreversible — use it only when you are satisfied.\n"
    "• Disputes are reviewed by a human arbitrator within 24 hours.\n"
    "• The service fee is 5% for deals over $100, or a flat $5 for deals under $100.\n\n"
    "_[Placeholder — update with your full terms.]_"
)

# TODO: Set your official verification channel username / link here.
VERIFICATION_CHANNEL = "https://t.me/your_verification_channel"


# ── Fee schedule ───────────────────────────────────────────────────────────────

FEE_SCHEDULE = "5% for deals over $100  •  Flat $5 for deals $100 and under"


# ── Helpers ────────────────────────────────────────────────────────────────────

def _ts(dt) -> str:
    if not dt:
        return "N/A"
    if isinstance(dt, str):
        return dt
    return dt.strftime("%Y-%m-%d %H:%M UTC")


# ── Public formatters ──────────────────────────────────────────────────────────

def format_welcome_dm(stats: Dict[str, int]) -> str:
    """Welcome message shown in DM after /start."""
    return (
        "🔒 *Trade Safe Bot — Crypto Escrow You Can Trust*\n\n"
        "We act as a neutral third party between buyer and seller. "
        "Your funds never touch the other party's hands until *you* confirm everything went as agreed.\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "🛡️ *Why traders choose us:*\n"
        "• Funds are held in our custody — not by the buyer, not by the seller\n"
        "• Every deal gets its own private group with a full audit trail\n"
        "• Buyer controls the release — seller only gets paid on confirmation\n"
        "• Disputes reviewed and resolved by our admin team within 24 h\n"
        "• No account, no KYC — just a wallet address\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 *Track record:*\n"
        f"  ✅ Deals completed: *{stats.get('completed', 0) + STATS_BASE_COMPLETED:,}*\n"
        f"  ⚖️ Disputes resolved: *{stats.get('disputes', 0) + STATS_BASE_DISPUTES:,}*\n\n"
        f"💰 *Fee:* {FEE_SCHEDULE}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "Choose an option below to get started:"
    )


def format_group_welcome(deal_number: str) -> str:
    """Message posted in the escrow group right after creation."""
    return (
        f"🔒 *Welcome to Escrow Group #{deal_number}*\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "📌 *Group Rules*\n"
        "• This group is strictly for *depositing and releasing payments only*.\n"
        "• All product discussions and delivery coordination must happen in private DMs.\n"
        "• Do not delete any messages — they serve as an audit trail.\n\n"
        f"💰 *Service fee:* {FEE_SCHEDULE}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "To begin, the *seller* should type:\n"
        "`/seller <your wallet address>`"
    )


def format_role_declaration(
    role: str,
    username: str,
    user_id: int,
    address: str,
    currency: str,
) -> str:
    """Role declaration block posted after /seller or /buyer."""
    role_emoji = "🛡️" if role == "seller" else "🛒"
    role_label = "SELLER" if role == "seller" else "BUYER"
    return (
        f"{role_emoji} *Escrow Role Declaration — {role_label}*\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 Username: @{username}\n"
        f"🆔 Telegram ID: `{user_id}`\n"
        f"📬 Wallet Address: `{address}`\n"
        f"💱 Detected Currency: *{currency}*\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    )


def format_transaction_summary(deal: Dict[str, Any]) -> str:
    """Full transaction summary posted once both roles are confirmed."""
    return (
        "✅ *Both roles confirmed — Transaction Summary*\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 Transaction ID: `{deal['deal_id']}`\n\n"
        f"🛡️ *Seller*\n"
        f"  Username: @{deal.get('seller_username')}\n"
        f"  Wallet: `{deal.get('seller_address')}`\n\n"
        f"🛒 *Buyer*\n"
        f"  Username: @{deal.get('buyer_username')}\n"
        f"  Wallet: `{deal.get('buyer_address')}`\n\n"
        f"💱 Currency: *{deal.get('currency')}*\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📬 *Escrow Deposit Address:*\n"
        f"`{deal.get('escrow_address')}`\n"
        "_Tap to copy_\n\n"
        f"⚠️ Before sending, verify this address in our official channel:\n"
        f"{VERIFICATION_CHANNEL}\n\n"
        "Type `/qr` to get a QR code of the deposit address.\n"
        "After sending, the admin will verify the deposit.\n"
        "Type `/balance` to check the status."
    )


def format_balance_status(deal: Dict[str, Any]) -> str:
    """Response to /balance — shows current deposit state."""
    status = deal.get("status")
    if status == "AWAITING_DEPOSIT":
        return (
            "⏳ *Balance Status*\n\n"
            "No confirmed deposit yet.\n"
            "Waiting for admin verification after funds are sent."
        )
    if status == "DEPOSITED":
        confirmations = deal.get("deposit_confirmations", 0)
        confirmed_at = _ts(deal.get("deposit_confirmed_at"))
        return (
            "✅ *Balance Status*\n\n"
            f"Deposit confirmed with {confirmations} confirmation(s).\n"
            f"Confirmed at: {confirmed_at}\n\n"
            "Funds are held in escrow. Once the seller delivers, "
            "the buyer should type `/pay_seller` to release funds."
        )
    if status == "COMPLETED":
        return (
            "🎉 *Balance Status*\n\n"
            f"Deal completed. Funds were released to the seller on {_ts(deal.get('released_at'))}."
        )
    if status == "REFUNDED":
        return (
            "↩️ *Balance Status*\n\n"
            f"Funds were refunded to the buyer on {_ts(deal.get('refunded_at'))}."
        )
    if status == "DISPUTED":
        return (
            "⚖️ *Balance Status*\n\n"
            "A dispute is open. An arbitrator is reviewing the case. "
            "Please keep the group active."
        )
    return f"ℹ️ Deal status: *{status}*"


def format_deposit_verified(deal: Dict[str, Any]) -> str:
    """Message posted in the group after admin runs /verify_deposit."""
    return (
        "✅ *Deposit Confirmed*\n\n"
        f"Transaction ID: `{deal.get('deposit_tx_hash', 'N/A')}`\n"
        f"Confirmations: {deal.get('deposit_confirmations', 0)}\n\n"
        "Funds are now held in escrow. The deal can proceed.\n\n"
        "Once the seller delivers, the buyer should type `/pay_seller` to release funds.\n"
        "⚠️ `/pay_seller` is irreversible — only use it when you are fully satisfied."
    )
