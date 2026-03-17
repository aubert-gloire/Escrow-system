"""
Database Models (MongoDB Document Schemas)
"""

from datetime import datetime
from typing import Optional, List, Dict, Any


class UserModel:
    """User document model."""
    
    @staticmethod
    def create(
        user_id: int,
        username: str,
        first_name: str,
        last_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create new user document."""
        return {
            "_id": user_id,
            "username": username,
            "first_name": first_name,
            "last_name": last_name,
            "role": None,  # "buyer" or "seller"
            "seller_addresses": {
                "BTC": None,
                "USDT": None,
                "LTC": None
            },
            "stats": {
                "completed_deals": 0,
                "total_deals": 0,
                "disputes_initiated": 0,
                "disputes_won": 0,
                "disputes_lost": 0
            },
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }


class DealModel:
    """Deal document model."""

    @staticmethod
    def create(
        deal_id: str,
        group_deal_number: str,
        creator_id: int,
        creator_username: str,
        group_id: Optional[int] = None,
        group_link: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a deal stub when the escrow group is first created.

        Roles, addresses, and currency are filled in later when both
        parties run /seller and /buyer inside the group.
        """
        return {
            "deal_id": deal_id,
            "group_deal_number": group_deal_number,
            "creator_id": creator_id,
            "creator_username": creator_username,
            # Seller fields — populated by /seller <ADDRESS>
            "seller_id": None,
            "seller_username": None,
            "seller_address": None,
            # Buyer fields — populated by /buyer <ADDRESS>
            "buyer_id": None,
            "buyer_username": None,
            "buyer_address": None,
            # Currency & escrow address — set once both roles are declared
            "currency": None,
            "escrow_address": None,
            # Deposit tracking — filled in by admin /verify_deposit
            "deposit_tx_hash": None,
            "deposit_confirmations": 0,
            "deposit_confirmed": False,
            "deposit_recorded_at": None,
            "deposit_confirmed_at": None,
            # Resolution timestamps
            "released_at": None,
            "refunded_at": None,
            # Dispute
            "dispute_reason": None,
            "dispute_initiated_by": None,
            # Status: SETUP → AWAITING_DEPOSIT → DEPOSITED → COMPLETED | REFUNDED | DISPUTED
            "status": "SETUP",
            # Group
            "group_id": group_id,
            "group_link": group_link,
            "group_created_at": datetime.utcnow() if group_id else None,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }


class TransactionModel:
    """Transaction document model."""
    
    @staticmethod
    def create(
        deal_id: str,
        tx_type: str,
        amount: float,
        currency: str,
        tx_hash: str,
        from_address: Optional[str] = None,
        to_address: Optional[str] = None,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create new transaction document."""
        return {
            "deal_id": deal_id,
            "type": tx_type,  # "deposit", "release", "refund"
            "amount": amount,
            "currency": currency,
            "tx_hash": tx_hash,
            "from_address": from_address,
            "to_address": to_address,
            "confirmations": 0,
            "confirmed": False,
            "recorded_at": datetime.utcnow(),
            "confirmed_at": None,
            "notes": notes
        }


class ConfigModel:
    """Config document model."""
    
    @staticmethod
    def get_default_addresses() -> Dict[str, Any]:
        """Get default config for escrow addresses."""
        return {
            "_id": "escrow_addresses",
            "BTC": None,
            "USDT": None,
            "LTC": None
        }
    
    @staticmethod
    def get_default_admin_settings() -> Dict[str, Any]:
        """Get default admin settings."""
        return {
            "_id": "admin_settings",
            "admin_user_ids": [],
            "max_deal_amount": 100000,
            "currency_confirmation_thresholds": {
                "BTC": 3,
                "USDT": 12,
                "LTC": 6
            }
        }
