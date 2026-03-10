"""
Message and data formatting utilities
"""

from datetime import datetime
from typing import Dict, Any


class Formatters:
    """Format messages and data for display."""
    
    @staticmethod
    def format_deal_info(deal: Dict[str, Any]) -> str:
        """Format deal info for display."""
        status_emoji = {
            "CREATED": "📝",
            "AWAITING_DEPOSIT": "⏳",
            "AWAITING_CONFIRMATION": "⏳",
            "DEPOSITED": "✅",
            "DELIVERED": "🚚",
            "COMPLETED": "🎉",
            "DISPUTED": "⚠️"
        }.get(deal.get("status"), "❓")
        
        return f"""
═══════════════════════════════
{status_emoji} DEAL #{deal.get('deal_id')}
═══════════════════════════════
Amount: {deal.get('amount')} {deal.get('currency')}
Description: {deal.get('description')}

Buyer: @{deal.get('buyer_username')}
Seller: @{deal.get('seller_username', 'TBD')}

Status: {deal.get('status')}
Created: {Formatters.format_timestamp(deal.get('created_at'))}
═══════════════════════════════
"""
    
    @staticmethod
    def format_deposit_instruction(deal: Dict[str, Any]) -> str:
        """Format deposit instructions for buyer."""
        return (
            f"📬 *DEPOSIT INSTRUCTIONS*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"Send `{deal.get('amount')} {deal.get('currency')}` to:\n\n"
            f"```\n{deal.get('escrow_address')}\n```\n\n"
            f"_tap address to copy_\n\n"
            f"After sending, run:\n"
            f"`/confirm_deposit {deal.get('deal_id')}` and paste your TX hash\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
    
    @staticmethod
    def format_deal_summary(deal: Dict[str, Any]) -> str:
        """Format complete deal summary."""
        seller_info = f"@{deal.get('seller_username')}" if deal.get('seller_username') else "TBD"
        group_link = f"[Join Group]({deal.get('group_link')})" if deal.get('group_link') else "N/A"
        
        return f"""
*ESCROW DEAL #{deal.get('deal_id')}*

*Amount:* {deal.get('amount')} {deal.get('currency')}
*Description:* {deal.get('description')}

*Buyer:* @{deal.get('buyer_username')}
*Seller:* {seller_info}

*Status:* {deal.get('status')}
*Group:* {group_link}

*Created:* {Formatters.format_timestamp(deal.get('created_at'))}
"""
    
    @staticmethod
    def format_timestamp(dt: datetime) -> str:
        """Format datetime to readable string."""
        if isinstance(dt, str):
            return dt
        return dt.strftime("%Y-%m-%d %H:%M:%S") if dt else "N/A"
    
    @staticmethod
    def format_user_stats(user: Dict[str, Any]) -> str:
        """Format user reputation stats."""
        stats = user.get('stats', {})
        return f"""
👤 User: @{user.get('username')}
Role: {user.get('role', 'Not set').upper()}

📊 Stats:
  • Completed Deals: {stats.get('completed_deals', 0)}
  • Total Deals: {stats.get('total_deals', 0)}
  • Disputes: {stats.get('disputes_initiated', 0)}
  • Win Rate: {Formatters.calculate_win_rate(stats)}%
"""
    
    @staticmethod
    def calculate_win_rate(stats: Dict[str, Any]) -> int:
        """Calculate dispute win rate."""
        total = stats.get('disputes_initiated', 0)
        if total == 0:
            return 0
        won = stats.get('disputes_won', 0)
        return int((won / total) * 100)
    
    @staticmethod
    def format_help_message() -> str:
        """Format help message."""
        return """
🔒 *Crypto Escrow Bot - Help*

*Available Commands:*

*User Commands:*
/start - Show main menu
/seller - Register as seller
/buyer - Register as buyer
/escrow - Create new escrow deal
/mydeals - View your active deals
/help - Show this help

*Deal Commands:*
/confirm_deposit {tx_hash} - Submit transaction hash
/delivered - Mark as delivered (seller)
/complete_deal - Confirm & complete deal (buyer)
/dispute - Raise dispute (buyer)

*Admin Commands:*
/verify_deposit {deal_id} - Verify deposit (admin)
/resolve_dispute {deal_id} {winner} - Resolve dispute (admin)

*Supported Currencies:* BTC, USDT, LTC

*How It Works:*
1. Register as buyer or seller
2. Create escrow deal
3. Buyer deposits to escrow address
4. Seller confirms delivery
5. Buyer confirms & completes
6. Funds released to seller

*Questions?* Contact admin for support.
"""
