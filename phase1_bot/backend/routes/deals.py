"""
Deals API Routes
"""

from fastapi import APIRouter, HTTPException, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from database.mongo import MongoDB
from database.crud import DealCRUD, UserCRUD
from pydantic import BaseModel
from typing import Optional
from loguru import logger


router = APIRouter()


class CreateDealRequest(BaseModel):
    """Create deal request."""
    buyer_id: int
    amount: float
    currency: str
    description: str


class DealResponse(BaseModel):
    """Deal response."""
    deal_id: str
    status: str
    amount: float
    currency: str
    buyer_id: int
    seller_id: Optional[int] = None


async def get_db() -> AsyncIOMotorDatabase:
    """Get database."""
    return MongoDB.get_db()


@router.post("/create")
async def create_deal(
    req: CreateDealRequest,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Create a new deal."""
    try:
        # Validate buyer exists
        buyer = await UserCRUD.get_user(db, req.buyer_id)
        if not buyer:
            raise HTTPException(status_code=404, detail="Buyer not found")
        
        # Generate deal ID
        import uuid
        deal_id = f"DEAL_{uuid.uuid4().hex[:8].upper()}"
        
        # Create deal
        result = await DealCRUD.create_deal(
            db,
            deal_id=deal_id,
            buyer_id=req.buyer_id,
            buyer_username=buyer.get("username"),
            amount=req.amount,
            currency=req.currency,
            description=req.description,
            escrow_address="pending"  # Will be set by bot
        )
        
        if result:
            return {
                "success": True,
                "deal_id": deal_id,
                "message": "Deal created successfully"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to create deal")
    
    except Exception as e:
        logger.error(f"Error creating deal: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{deal_id}")
async def get_deal(
    deal_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Get deal by ID."""
    try:
        deal = await DealCRUD.get_deal(db, deal_id)
        
        if not deal:
            raise HTTPException(status_code=404, detail="Deal not found")
        
        return {
            "success": True,
            "deal": deal
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting deal: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/user/{user_id}")
async def get_user_deals(
    user_id: int,
    role: str = "buyer",
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Get deals for a user."""
    try:
        deals = await DealCRUD.get_user_deals(db, user_id, role)
        
        return {
            "success": True,
            "deals": deals,
            "count": len(deals)
        }
    
    except Exception as e:
        logger.error(f"Error getting user deals: {e}")
        raise HTTPException(status_code=500, detail=str(e))
