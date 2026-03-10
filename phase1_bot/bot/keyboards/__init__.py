"""
Telegram Inline and Reply Keyboards
"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton


class MainMenuKeyboard:
    """Main menu keyboard."""
    
    @staticmethod
    def get_main_menu() -> InlineKeyboardMarkup:
        """Get main menu inline keyboard."""
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🛡️ Register as Seller", callback_data="role_seller")],
                [InlineKeyboardButton(text="🛒 Register as Buyer", callback_data="role_buyer")],
                [InlineKeyboardButton(text="📋 Create Escrow Deal", callback_data="create_deal")],
                [InlineKeyboardButton(text="💼 My Deals", callback_data="my_deals")],
                [InlineKeyboardButton(text="❓ Help", callback_data="help")]
            ]
        )


class RoleKeyboard:
    """Role selection keyboard."""
    
    @staticmethod
    def get_currency_selection() -> InlineKeyboardMarkup:
        """Get currency selection keyboard."""
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="₿ Bitcoin", callback_data="currency_BTC")],
                [InlineKeyboardButton(text="💵 USDT (TRC20)", callback_data="currency_USDT")],
                [InlineKeyboardButton(text="Ξ Ethereum", callback_data="currency_ETH")],
                [InlineKeyboardButton(text="Ł Litecoin", callback_data="currency_LTC")],
                [InlineKeyboardButton(text="❌ Cancel", callback_data="cancel")]
            ]
        )


class DealActionKeyboard:
    """Deal action keyboard."""
    
    @staticmethod
    def get_deal_actions(deal_id: str, status: str) -> InlineKeyboardMarkup:
        """Get deal action keyboard based on status."""
        buttons = []
        
        if status == "DEPOSITED":
            buttons.append([InlineKeyboardButton(text="🚚 Mark Delivered", callback_data=f"delivered_{deal_id}")])
        
        if status == "DELIVERED":
            buttons.append([InlineKeyboardButton(text="✅ Confirm & Complete", callback_data=f"complete_{deal_id}")])
            buttons.append([InlineKeyboardButton(text="❌ Raise Dispute", callback_data=f"dispute_{deal_id}")])
        
        buttons.append([InlineKeyboardButton(text="📖 View Details", callback_data=f"view_deal_{deal_id}")])
        buttons.append([InlineKeyboardButton(text="⬅️ Back", callback_data="back_to_menu")])
        
        return InlineKeyboardMarkup(inline_keyboard=buttons)
    
    @staticmethod
    def get_deposit_confirmation(deal_id: str) -> InlineKeyboardMarkup:
        """Get deposit confirmation keyboard."""
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="✅ Confirm Deposit", callback_data=f"confirm_deposit_{deal_id}")],
                [InlineKeyboardButton(text="📖 View Deal", callback_data=f"view_deal_{deal_id}")],
                [InlineKeyboardButton(text="⬅️ Back", callback_data="back_to_menu")]
            ]
        )
    
    @staticmethod
    def get_dispute_resolution(deal_id: str) -> InlineKeyboardMarkup:
        """Get dispute resolution keyboard (admin only)."""
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🏆 Buyer Wins", callback_data=f"resolve_buyer_{deal_id}")],
                [InlineKeyboardButton(text="💼 Seller Wins", callback_data=f"resolve_seller_{deal_id}")],
            ]
        )


class ConfirmationKeyboard:
    """Confirmation keyboard."""
    
    @staticmethod
    def get_yes_no() -> InlineKeyboardMarkup:
        """Get yes/no confirmation keyboard."""
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="✅ Yes", callback_data="confirm_yes"),
                    InlineKeyboardButton(text="❌ No", callback_data="confirm_no")
                ]
            ]
        )
    
    @staticmethod
    def get_cancel() -> InlineKeyboardMarkup:
        """Get cancel button keyboard."""
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="❌ Cancel", callback_data="cancel")]
            ]
        )


class GroupJoinKeyboard:
    """Group join keyboard."""
    
    @staticmethod
    def get_group_actions(group_link: str, deal_id: str) -> InlineKeyboardMarkup:
        """Get group action keyboard."""
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="👥 Join Group", url=group_link)],
                [InlineKeyboardButton(text="📖 View Deal", callback_data=f"view_deal_{deal_id}")],
                [InlineKeyboardButton(text="⬅️ Back", callback_data="back_to_menu")]
            ]
        )
