"""
MongoDB Connection and Management
"""

import asyncio
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from config.settings import settings
from loguru import logger


class MongoDB:
    """MongoDB connection manager."""
    
    client: AsyncIOMotorClient = None
    db: AsyncIOMotorDatabase = None
    
    @classmethod
    async def connect_db(cls):
        """Connect to MongoDB."""
        if not settings.mongo_uri:
            raise RuntimeError("MONGO_URI is not set")

        max_attempts = 5

        for attempt in range(1, max_attempts + 1):
            try:
                cls.client = AsyncIOMotorClient(
                    settings.mongo_uri,
                    serverSelectionTimeoutMS=10000,
                    connectTimeoutMS=10000,
                    socketTimeoutMS=20000,
                    maxPoolSize=50,
                    minPoolSize=1,
                )
                cls.db = cls.client[settings.mongo_db_name]

                # Test connection
                await cls.db.command("ping")
                logger.info(f"✅ Connected to MongoDB: {settings.mongo_db_name}")

                # Create indexes
                await cls._create_indexes()
                return

            except Exception as e:
                logger.warning(
                    f"MongoDB connection attempt {attempt}/{max_attempts} failed: {e}"
                )

                if cls.client:
                    cls.client.close()
                    cls.client = None
                    cls.db = None

                if attempt == max_attempts:
                    logger.error("❌ Failed to connect to MongoDB after retries")
                    raise

                await asyncio.sleep(min(2 * attempt, 10))
    
    @classmethod
    async def close_db(cls):
        """Close MongoDB connection."""
        if cls.client:
            cls.client.close()
            logger.info("✅ Disconnected from MongoDB")
    
    @classmethod
    async def _create_indexes(cls):
        """Create necessary database indexes."""
        try:
            # Users collection
            await cls.db.users.create_index("username")
            await cls.db.users.create_index("role")
            
            # Deals collection
            await cls.db.deals.create_index("deal_id", unique=True)
            await cls.db.deals.create_index("buyer_id")
            await cls.db.deals.create_index("seller_id")
            await cls.db.deals.create_index("status")
            await cls.db.deals.create_index("currency")
            await cls.db.deals.create_index("group_id")
            
            # Transactions collection
            await cls.db.transactions.create_index("deal_id")
            await cls.db.transactions.create_index("tx_hash")
            
            logger.debug("✅ Indexes created")
        except Exception as e:
            logger.warning(f"Index creation error (may already exist): {e}")
    
    @classmethod
    def get_db(cls) -> AsyncIOMotorDatabase:
        """Get the database instance."""
        if cls.db is None:
            raise RuntimeError("Database not connected. Call connect_db() first.")
        return cls.db


# Export for convenience
async def get_db() -> AsyncIOMotorDatabase:
    """Get database instance."""
    return MongoDB.get_db()
