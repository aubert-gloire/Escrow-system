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
        buyer_id: int,
        buyer_username: str,
        amount: float,
        currency: str,
        description: str,
        escrow_address: str,
        seller_id: Optional[int] = None,
        seller_username: Optional[str] = None,
        seller_address: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create new deal document."""
        return {
            "deal_id": deal_id,
            "buyer_id": buyer_id,
            "buyer_username": buyer_username,
            "seller_id": seller_id,
            "seller_username": seller_username,
            "amount": amount,
            "currency": currency,
            "description": description,
            "escrow_address": escrow_address,
            "seller_address": seller_address,
            "deposit_tx_hash": None,
            "deposit_amount": None,
            "deposit_confirmations": 0,
            "deposit_confirmed": False,
            "deposit_recorded_at": None,
            "deposit_confirmed_at": None,
            "status": "CREATED",  # CREATED → AWAITING_DEPOSIT → DEPOSITED → DELIVERED → COMPLETED
            "delivery_confirmed_at": None,
            "dispute_status": None,
            "dispute_reason": None,
            "dispute_initiated_by": None,
            "dispute_resolved": False,
            "dispute_winner": None,
            "group_id": None,
            "group_link": None,
            "group_created_at": None,
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
