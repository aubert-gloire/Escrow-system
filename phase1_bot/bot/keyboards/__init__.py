"""
Telegram Inline Keyboards
"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


class MainMenuKeyboard:
    """DM main menu — shown after /start."""

    @staticmethod
    def get_main_menu() -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="❓ What is Escrow", callback_data="what_is_escrow")],
                [InlineKeyboardButton(text="📋 Instructions", callback_data="instructions")],
                [InlineKeyboardButton(text="📜 Terms & Conditions", callback_data="terms")],
                [InlineKeyboardButton(text="🔒 Create Escrow Group", callback_data="create_deal")],
            ]
        )

    @staticmethod
    def get_back_to_menu() -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Back to Menu", callback_data="back_to_menu")]
            ]
        )


class CreateGroupKeyboard:
    """Keyboards used during / after group creation."""

    @staticmethod
    def get_join_group(group_link: str) -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="👥 Join Escrow Group", url=group_link)],
            ]
        )


class GroupActionKeyboard:
    """Keyboards used inside the escrow group."""

    @staticmethod
    def get_pay_seller_confirm(deal_id: str) -> InlineKeyboardMarkup:
        """Shown before /pay_seller is finalised — warns it is irreversible."""
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="✅ Yes, release funds (IRREVERSIBLE)",
                        callback_data=f"pay_seller_confirm_{deal_id}",
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="❌ Cancel", callback_data=f"pay_seller_cancel_{deal_id}"
                    )
                ],
            ]
        )
