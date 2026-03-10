"""
CRUD Operations for MongoDB
"""

from motor.motor_asyncio import AsyncIOMotorDatabase
from database.models import UserModel, DealModel, TransactionModel
from typing import Optional, List, Dict, Any
from loguru import logger
from datetime import datetime


class UserCRUD:
    """User CRUD operations."""
    
    @staticmethod
    async def create_user(db: AsyncIOMotorDatabase, user_id: int, username: str, first_name: str, last_name: Optional[str] = None) -> bool:
        """Create a new user."""
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
        """Get user by ID."""
        try:
            return await db.users.find_one({"_id": user_id})
        except Exception as e:
            logger.error(f"Error getting user: {e}")
            return None
    
    @staticmethod
    async def update_user_role(db: AsyncIOMotorDatabase, user_id: int, role: str) -> bool:
        """Update user role."""
        try:
            result = await db.users.update_one(
                {"_id": user_id},
                {"$set": {"role": role, "updated_at": datetime.utcnow()}}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error updating user role: {e}")
            return False
    
    @staticmethod
    async def update_seller_address(db: AsyncIOMotorDatabase, user_id: int, currency: str, address: str) -> bool:
        """Update seller's cryptocurrency address."""
        try:
            result = await db.users.update_one(
                {"_id": user_id},
                {"$set": {f"seller_addresses.{currency}": address, "updated_at": datetime.utcnow()}}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error updating seller address: {e}")
            return False
    
    @staticmethod
    async def get_user_by_username(db: AsyncIOMotorDatabase, username: str) -> Optional[Dict[str, Any]]:
        """Get user by username."""
        try:
            return await db.users.find_one({"username": username})
        except Exception as e:
            logger.error(f"Error getting user by username: {e}")
            return None


class DealCRUD:
    """Deal CRUD operations."""
    
    @staticmethod
    async def create_deal(
        db: AsyncIOMotorDatabase,
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
    ) -> Optional[str]:
        """Create a new deal."""
        try:
            deal_doc = DealModel.create(
                deal_id, buyer_id, buyer_username, amount, currency, description,
                escrow_address, seller_id, seller_username, seller_address
            )
            result = await db.deals.insert_one(deal_doc)
            logger.info(f"Created deal {deal_id}")
            return deal_id
        except Exception as e:
            logger.error(f"Error creating deal: {e}")
            return None
    
    @staticmethod
    async def get_deal(db: AsyncIOMotorDatabase, deal_id: str) -> Optional[Dict[str, Any]]:
        """Get deal by ID."""
        try:
            return await db.deals.find_one({"deal_id": deal_id})
        except Exception as e:
            logger.error(f"Error getting deal: {e}")
            return None
    
    @staticmethod
    async def update_deal_status(db: AsyncIOMotorDatabase, deal_id: str, status: str) -> bool:
        """Update deal status."""
        try:
            result = await db.deals.update_one(
                {"deal_id": deal_id},
                {"$set": {"status": status, "updated_at": datetime.utcnow()}}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error updating deal status: {e}")
            return False
    
    @staticmethod
    async def record_deposit(
        db: AsyncIOMotorDatabase,
        deal_id: str,
        tx_hash: str,
        amount: float
    ) -> bool:
        """Record deposit for a deal."""
        try:
            result = await db.deals.update_one(
                {"deal_id": deal_id},
                {
                    "$set": {
                        "deposit_tx_hash": tx_hash,
                        "deposit_amount": amount,
                        "deposit_recorded_at": datetime.utcnow(),
                        "status": "AWAITING_CONFIRMATION",
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error recording deposit: {e}")
            return False
    
    @staticmethod
    async def confirm_deposit(
        db: AsyncIOMotorDatabase,
        deal_id: str,
        confirmations: int
    ) -> bool:
        """Confirm deposit for a deal."""
        try:
            result = await db.deals.update_one(
                {"deal_id": deal_id},
                {
                    "$set": {
                        "deposit_confirmed": True,
                        "deposit_confirmations": confirmations,
                        "deposit_confirmed_at": datetime.utcnow(),
                        "status": "DEPOSITED",
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error confirming deposit: {e}")
            return False
    
    @staticmethod
    async def create_group(
        db: AsyncIOMotorDatabase,
        deal_id: str,
        group_id: int,
        group_link: str
    ) -> bool:
        """Create group for deal."""
        try:
            result = await db.deals.update_one(
                {"deal_id": deal_id},
                {
                    "$set": {
                        "group_id": group_id,
                        "group_link": group_link,
                        "group_created_at": datetime.utcnow(),
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error creating group: {e}")
            return False
    
    @staticmethod
    async def mark_delivered(db: AsyncIOMotorDatabase, deal_id: str) -> bool:
        """Mark deal as delivered."""
        try:
            result = await db.deals.update_one(
                {"deal_id": deal_id},
                {
                    "$set": {
                        "status": "DELIVERED",
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error marking as delivered: {e}")
            return False
    
    @staticmethod
    async def complete_deal(db: AsyncIOMotorDatabase, deal_id: str) -> bool:
        """Complete a deal."""
        try:
            result = await db.deals.update_one(
                {"deal_id": deal_id},
                {
                    "$set": {
                        "status": "COMPLETED",
                        "delivery_confirmed_at": datetime.utcnow(),
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error completing deal: {e}")
            return False
    
    @staticmethod
    async def update_seller_info(
        db: AsyncIOMotorDatabase,
        deal_id: str,
        seller_id: int,
        seller_username: str,
        seller_address: str
    ) -> bool:
        """Update seller info in deal."""
        try:
            result = await db.deals.update_one(
                {"deal_id": deal_id},
                {
                    "$set": {
                        "seller_id": seller_id,
                        "seller_username": seller_username,
                        "seller_address": seller_address,
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error updating seller info: {e}")
            return False
    
    @staticmethod
    async def raise_dispute(
        db: AsyncIOMotorDatabase,
        deal_id: str,
        initiated_by: int,
        reason: str
    ) -> bool:
        """Raise dispute for a deal."""
        try:
            result = await db.deals.update_one(
                {"deal_id": deal_id},
                {
                    "$set": {
                        "dispute_status": "DISPUTED",
                        "dispute_reason": reason,
                        "dispute_initiated_by": initiated_by,
                        "status": "DISPUTED",
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error raising dispute: {e}")
            return False
    
    @staticmethod
    async def resolve_dispute(
        db: AsyncIOMotorDatabase,
        deal_id: str,
        winner: str
    ) -> bool:
        """Resolve dispute for a deal."""
        try:
            result = await db.deals.update_one(
                {"deal_id": deal_id},
                {
                    "$set": {
                        "dispute_resolved": True,
                        "dispute_winner": winner,
                        "status": "COMPLETED",
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error resolving dispute: {e}")
            return False
    
    @staticmethod
    async def get_user_deals(
        db: AsyncIOMotorDatabase,
        user_id: int,
        role: str
    ) -> List[Dict[str, Any]]:
        """Get all deals for a user."""
        try:
            if role == "buyer":
                query = {"buyer_id": user_id}
            else:
                query = {"seller_id": user_id}
            
            return await db.deals.find(query).to_list(None)
        except Exception as e:
            logger.error(f"Error getting user deals: {e}")
            return []


class TransactionCRUD:
    """Transaction CRUD operations."""
    
    @staticmethod
    async def create_transaction(
        db: AsyncIOMotorDatabase,
        deal_id: str,
        tx_type: str,
        amount: float,
        currency: str,
        tx_hash: str,
        from_address: Optional[str] = None,
        to_address: Optional[str] = None,
        notes: Optional[str] = None
    ) -> bool:
        """Create a new transaction record."""
        try:
            transaction = TransactionModel.create(
                deal_id, tx_type, amount, currency, tx_hash,
                from_address, to_address, notes
            )
            await db.transactions.insert_one(transaction)
            logger.info(f"Created transaction for deal {deal_id}")
            return True
        except Exception as e:
            logger.error(f"Error creating transaction: {e}")
            return False
    
    @staticmethod
    async def get_deal_transactions(
        db: AsyncIOMotorDatabase,
        deal_id: str
    ) -> List[Dict[str, Any]]:
        """Get all transactions for a deal."""
        try:
            return await db.transactions.find({"deal_id": deal_id}).to_list(None)
        except Exception as e:
            logger.error(f"Error getting transactions: {e}")
            return []
