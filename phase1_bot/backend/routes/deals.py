"""
Deals API Routes
"""

from fastapi import APIRouter, HTTPException, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from database.mongo import MongoDB
from database.crud import DealCRUD
from loguru import logger


router = APIRouter()


async def get_db() -> AsyncIOMotorDatabase:
    return MongoDB.get_db()


@router.get("/stats")
async def get_stats(db: AsyncIOMotorDatabase = Depends(get_db)):
    """Return completed deal count and resolved dispute count."""
    try:
        stats = await DealCRUD.get_stats(db)
        return {"success": True, "stats": stats}
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{deal_id}")
async def get_deal(
    deal_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Get deal by ID."""
    try:
        deal = await DealCRUD.get_deal(db, deal_id.upper())
        if not deal:
            raise HTTPException(status_code=404, detail="Deal not found")
        # Strip internal MongoDB _id before returning
        deal.pop("_id", None)
        return {"success": True, "deal": deal}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting deal: {e}")
        raise HTTPException(status_code=500, detail=str(e))
