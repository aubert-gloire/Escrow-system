"""
Admin API Routes
"""

from fastapi import APIRouter, HTTPException, Depends, Header
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel
from database.mongo import MongoDB
from database.crud import DealCRUD
from config.settings import settings
from loguru import logger
from typing import Optional


router = APIRouter()


async def get_db() -> AsyncIOMotorDatabase:
    return MongoDB.get_db()


def verify_admin_key(x_api_key: Optional[str] = Header(default=None)):
    """Require a valid admin API key via X-Api-Key header."""
    if not settings.secret_key:
        raise HTTPException(status_code=500, detail="Admin API key not configured on server")
    if x_api_key != settings.secret_key:
        raise HTTPException(status_code=401, detail="Unauthorized")


class VerifyDepositRequest(BaseModel):
    tx_hash: str
    confirmations: int = 1


@router.post("/verify-deposit/{deal_id}")
async def verify_deposit(
    deal_id: str,
    body: VerifyDepositRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
    _: None = Depends(verify_admin_key),
):
    """Confirm a deposit was received. Sets deal status to DEPOSITED."""
    try:
        success = await DealCRUD.confirm_deposit(
            db, deal_id.upper(), body.tx_hash, body.confirmations
        )
        if success:
            return {
                "success": True,
                "message": f"Deposit verified ({body.confirmations} confirmations)",
            }
        raise HTTPException(status_code=400, detail="Failed to verify deposit — check deal ID")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying deposit: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/refund-buyer/{deal_id}")
async def refund_buyer(
    deal_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    _: None = Depends(verify_admin_key),
):
    """Refund funds to the buyer. Sets deal status to REFUNDED."""
    try:
        deal = await DealCRUD.get_deal(db, deal_id.upper())
        if not deal:
            raise HTTPException(status_code=404, detail="Deal not found")
        if deal.get("status") in ("COMPLETED", "REFUNDED"):
            raise HTTPException(
                status_code=400,
                detail=f"Deal is already {deal.get('status')}",
            )
        if await DealCRUD.refund_to_buyer(db, deal_id.upper()):
            return {"success": True, "message": "Funds refunded to buyer"}
        raise HTTPException(status_code=400, detail="Failed to refund")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error refunding buyer: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/release-to-seller/{deal_id}")
async def release_to_seller(
    deal_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    _: None = Depends(verify_admin_key),
):
    """Release funds to the seller. Sets deal status to COMPLETED."""
    try:
        deal = await DealCRUD.get_deal(db, deal_id.upper())
        if not deal:
            raise HTTPException(status_code=404, detail="Deal not found")
        if deal.get("status") != "DEPOSITED":
            raise HTTPException(
                status_code=400,
                detail=f"Deal status is {deal.get('status')} — funds can only be released from DEPOSITED",
            )
        if await DealCRUD.release_to_seller(db, deal_id.upper()):
            return {"success": True, "message": "Funds released to seller"}
        raise HTTPException(status_code=400, detail="Failed to release funds")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error releasing to seller: {e}")
        raise HTTPException(status_code=500, detail=str(e))
