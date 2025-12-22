"""WhatsApp API endpoints for sending recipes"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from annapurna.models.base import get_db
from annapurna.services.whatsapp_service import whatsapp_service

router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])


class SendToMaidRequest(BaseModel):
    user_id: str
    recipe_id: str


class SendToMaidResponse(BaseModel):
    status: str
    message: str
    sent_to: str = None


@router.post("/send-to-maid", response_model=SendToMaidResponse)
def send_recipe_to_maid(
    request: SendToMaidRequest,
    db: Session = Depends(get_db)
):
    """
    Send a recipe to the user's maid via WhatsApp.

    The maid's phone number is retrieved from the user's profile
    (set during onboarding step 5).
    """
    success, message = whatsapp_service.send_recipe_to_maid(
        user_id=request.user_id,
        recipe_id=request.recipe_id,
        db=db
    )

    if not success:
        raise HTTPException(status_code=400, detail=message)

    # Get maid phone for response
    maid_phone = whatsapp_service.get_maid_phone(request.user_id, db)

    return SendToMaidResponse(
        status="success",
        message=message,
        sent_to=maid_phone
    )


@router.get("/check-maid/{user_id}")
def check_maid_configured(user_id: str, db: Session = Depends(get_db)):
    """Check if user has a maid phone number configured"""
    maid_phone = whatsapp_service.get_maid_phone(user_id, db)

    return {
        "has_maid": maid_phone is not None,
        "maid_phone": maid_phone[:4] + "****" + maid_phone[-2:] if maid_phone else None
    }
