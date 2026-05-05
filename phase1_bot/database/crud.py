"""
CRUD Operations for MongoDB
"""

from motor.motor_asyncio import AsyncIOMotorDatabase
from database.models import UserModel, DealModel
from typing import Optional, List, Dict, Any
from loguru import logger
from datetime import datetime, timezone


def _now():
    return datetime.now(timezone.utc)


class UserCRUD:
    """User CRUD operations."""

    @staticmethod
    async def create_user(
        db: AsyncIOMotorDatabase,
        user_id: int,
        username: str,
        first_name: str,
        last_name: Optional[str] = None
    ) -> bool:
        try:
            user_doc = UserModel.create(user_id, username, first_name, last_name)
            await db.users.insert_one(user_doc)
            logger.info(f"Created user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            return False

    @staticmethod
    async def get_user(db: AsyncIOMotorDatabase, user_id: int) -> Optional[Dict[str, Any]]:
        try:
            return await db.users.find_one({"_id": user_id})
        except Exception as e:
            logger.error(f"Error getting user: {e}")
            return None


class DealCRUD:
    """Deal CRUD operations."""

    @staticmethod
    async def create_deal(
        db: AsyncIOMotorDatabase,
        deal_id: str,
        group_deal_number: str,
        creator_id: int,
        creator_username: str,
        group_id: Optional[int] = None,
        group_link: Optional[str] = None,
    ) -> Optional[str]:
        """Create the initial deal stub when the escrow group is created."""
        try:
            deal_doc = DealModel.create(
                deal_id=deal_id,
                group_deal_number=group_deal_number,
                creator_id=creator_id,
                creator_username=creator_username,
                group_id=group_id,
                group_link=group_link,
            )
            await db.deals.insert_one(deal_doc)
            logger.info(f"Created deal {deal_id} for group #{group_deal_number}")
            return deal_id
        except Exception as e:
            logger.error(f"Error creating deal: {e}")
            return None

    @staticmethod
    async def get_deal(db: AsyncIOMotorDatabase, deal_id: str) -> Optional[Dict[str, Any]]:
        try:
            return await db.deals.find_one({"deal_id": deal_id})
        except Exception as e:
            logger.error(f"Error getting deal: {e}")
            return None

    @staticmethod
    async def get_deal_by_group_id(db: AsyncIOMotorDatabase, group_id: int) -> Optional[Dict[str, Any]]:
        """Find the deal associated with a Telegram group."""
        try:
            return await db.deals.find_one({"group_id": group_id})
        except Exception as e:
            logger.error(f"Error getting deal by group_id: {e}")
            return None

    @staticmethod
    async def get_stats(db: AsyncIOMotorDatabase) -> Dict[str, int]:
        """Return live counts for the /start welcome message."""
        try:
            completed = await db.deals.count_documents({"status": "COMPLETED"})
            disputes = await db.deals.count_documents({"status": {"$in": ["DISPUTED", "REFUNDED"]}})
            return {"completed": completed, "disputes": disputes}
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {"completed": 0, "disputes": 0}

    @staticmethod
    async def update_seller_in_deal(
        db: AsyncIOMotorDatabase,
        deal_id: str,
        seller_id: int,
        seller_username: str,
        seller_address: str,
        currency: str,
    ) -> bool:
        """Set seller info after /seller <ADDRESS> is run in the group."""
        try:
            result = await db.deals.update_one(
                {"deal_id": deal_id},
                {
                    "$set": {
                        "seller_id": seller_id,
                        "seller_username": seller_username,
                        "seller_address": seller_address,
                        "currency": currency,
                        "updated_at": _now(),
                    }
                },
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error updating seller in deal: {e}")
            return False

    @staticmethod
    async def update_buyer_in_deal(
        db: AsyncIOMotorDatabase,
        deal_id: str,
        buyer_id: int,
        buyer_username: str,
        buyer_address: str,
        escrow_address: str,
    ) -> bool:
        """Set buyer info and advance status to AWAITING_DEPOSIT."""
        try:
            result = await db.deals.update_one(
                {"deal_id": deal_id},
                {
                    "$set": {
                        "buyer_id": buyer_id,
                        "buyer_username": buyer_username,
                        "buyer_address": buyer_address,
                        "escrow_address": escrow_address,
                        "status": "AWAITING_DEPOSIT",
                        "updated_at": _now(),
                    }
                },
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error updating buyer in deal: {e}")
            return False

    @staticmethod
    async def reset_roles(db: AsyncIOMotorDatabase, deal_id: str) -> bool:
        """Clear both role declarations so parties can re-declare."""
        try:
            result = await db.deals.update_one(
                {"deal_id": deal_id},
                {
                    "$set": {
                        "seller_id": None,
                        "seller_username": None,
                        "seller_address": None,
                        "buyer_id": None,
                        "buyer_username": None,
                        "buyer_address": None,
                        "currency": None,
                        "escrow_address": None,
                        "status": "SETUP",
                        "updated_at": _now(),
                    }
                },
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error resetting roles: {e}")
            return False

    @staticmethod
    async def claim_payment(
        db: AsyncIOMotorDatabase,
        deal_id: str,
        tx_hash: str,
    ) -> bool:
        """Buyer records a payment claim — stores TX hash for admin to verify."""
        try:
            result = await db.deals.update_one(
                {"deal_id": deal_id, "status": "AWAITING_DEPOSIT"},
                {
                    "$set": {
                        "payment_tx_claimed": tx_hash,
                        "payment_claimed_at": _now(),
                        "updated_at": _now(),
                    }
                },
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error claiming payment: {e}")
            return False

    @staticmethod
    async def confirm_deposit(
        db: AsyncIOMotorDatabase,
        deal_id: str,
        tx_hash: str,
        confirmations: int,
        verified_amount: Optional[float] = None,
    ) -> bool:
        """Admin confirms the deposit was received on-chain."""
        try:
            fields = {
                "deposit_tx_hash": tx_hash,
                "deposit_confirmed": True,
                "deposit_confirmations": confirmations,
                "deposit_confirmed_at": _now(),
                "status": "DEPOSITED",
                "updated_at": _now(),
            }
            if verified_amount is not None:
                fields["verified_amount"] = verified_amount
            result = await db.deals.update_one(
                {"deal_id": deal_id, "status": "AWAITING_DEPOSIT"},
                {"$set": fields},
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error confirming deposit: {e}")
            return False

    @staticmethod
    async def release_to_seller(db: AsyncIOMotorDatabase, deal_id: str) -> bool:
        """Buyer releases funds — deal is completed, irreversible."""
        try:
            result = await db.deals.update_one(
                {"deal_id": deal_id},
                {
                    "$set": {
                        "status": "COMPLETED",
                        "released_at": _now(),
                        "updated_at": _now(),
                    }
                },
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error releasing to seller: {e}")
            return False

    @staticmethod
    async def refund_to_buyer(db: AsyncIOMotorDatabase, deal_id: str) -> bool:
        """Admin refunds funds to buyer."""
        try:
            result = await db.deals.update_one(
                {"deal_id": deal_id},
                {
                    "$set": {
                        "status": "REFUNDED",
                        "refunded_at": _now(),
                        "updated_at": _now(),
                    }
                },
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error refunding to buyer: {e}")
            return False

    @staticmethod
    async def open_dispute(
        db: AsyncIOMotorDatabase,
        deal_id: str,
        initiated_by: int,
    ) -> bool:
        """Mark a deal as disputed after /contact is used."""
        try:
            result = await db.deals.update_one(
                {"deal_id": deal_id},
                {
                    "$set": {
                        "status": "DISPUTED",
                        "dispute_initiated_by": initiated_by,
                        "updated_at": _now(),
                    }
                },
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error opening dispute: {e}")
            return False

    @staticmethod
    async def update_deal_status(db: AsyncIOMotorDatabase, deal_id: str, status: str) -> bool:
        """Generic status update (used by admin fallbacks)."""
        try:
            result = await db.deals.update_one(
                {"deal_id": deal_id},
                {"$set": {"status": status, "updated_at": _now()}},
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error updating deal status: {e}")
            return False
