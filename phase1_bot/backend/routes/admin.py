"""
Admin API Routes
"""

from fastapi import APIRouter, HTTPException, Depends, Header
from motor.motor_asyncio import AsyncIOMotorDatabase
from database.mongo import MongoDB
from database.crud import DealCRUD
from config.settings import settings
from loguru import logger
from typing import Optional


router = APIRouter()


async def get_db() -> AsyncIOMotorDatabase:
    """Get database."""
    return MongoDB.get_db()


def verify_admin_key(x_api_key: Optional[str] = Header(default=None)):
    """Require a valid admin API key via X-Api-Key header."""
    if not settings.secret_key:
        raise HTTPException(status_code=500, detail="Admin API key not configured on server")
    if x_api_key != settings.secret_key:
        raise HTTPException(status_code=401, detail="Unauthorized")


@router.post("/verify-deposit/{deal_id}")
async def verify_deposit(
    deal_id: str,
    confirmations: int = 3,
    db: AsyncIOMotorDatabase = Depends(get_db),
    _: None = Depends(verify_admin_key)
):
    """Verify deposit for a deal (admin only)."""
    try:
        if await DealCRUD.confirm_deposit(db, deal_id, confirmations):
            return {
                "success": True,
                "message": f"Deposit verified with {confirmations} confirmations"
            }
        else:
            raise HTTPException(status_code=400, detail="Failed to verify deposit")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying deposit: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/resolve-dispute/{deal_id}")
async def resolve_dispute(
    deal_id: str,
    winner: str = "buyer",
    db: AsyncIOMotorDatabase = Depends(get_db),
    _: None = Depends(verify_admin_key)
):
    """Resolve a dispute (admin only)."""
    try:
        if winner not in ["buyer", "seller"]:
            raise HTTPException(status_code=400, detail="Winner must be 'buyer' or 'seller'")

        # Resolve dispute
        if await DealCRUD.resolve_dispute(db, deal_id, winner):
            return {
                "success": True,
                "message": f"Dispute resolved - {winner} wins"
            }
        else:
            raise HTTPException(status_code=400, detail="Failed to resolve dispute")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resolving dispute: {e}")
        raise HTTPException(status_code=500, detail=str(e))
