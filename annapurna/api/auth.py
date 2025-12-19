"""Authentication API for mobile app"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import uuid
from typing import Optional
from datetime import datetime

router = APIRouter(prefix="/v1/auth", tags=["Authentication"])


# Request/Response models
class SendOTPRequest(BaseModel):
    mobile_number: str


class SendOTPResponse(BaseModel):
    status: str
    message: str
    mobile_number: str


class VerifyOTPRequest(BaseModel):
    mobile_number: str
    otp: str


class VerifyOTPResponse(BaseModel):
    status: str
    message: str
    user_id: str
    email: str
    name: str
    session_token: str
    mobile_number: str


# Hardcoded OTP for development
DEV_OTP = "123456"

# In-memory storage for dev (in production, use Redis)
sent_otps = {}


@router.post("/send-otp", response_model=SendOTPResponse)
async def send_otp(request: SendOTPRequest):
    """
    Send OTP to mobile number (mock for development)

    For testing: Always returns success, OTP is always "123456"
    """
    mobile = request.mobile_number.strip()

    if not mobile or len(mobile) < 10:
        raise HTTPException(status_code=400, detail="Invalid mobile number")

    # In dev mode, just store the mobile number
    sent_otps[mobile] = {
        "otp": DEV_OTP,
        "sent_at": datetime.utcnow().isoformat()
    }

    return SendOTPResponse(
        status="success",
        message=f"OTP sent to {mobile}. For testing, use OTP: {DEV_OTP}",
        mobile_number=mobile
    )


@router.post("/verify-otp", response_model=VerifyOTPResponse)
async def verify_otp(request: VerifyOTPRequest):
    """
    Verify OTP and login user

    For testing: OTP is always "123456"
    Creates a new user if mobile number doesn't exist
    """
    mobile = request.mobile_number.strip()
    otp = request.otp.strip()

    # Verify OTP (hardcoded for dev)
    if otp != DEV_OTP:
        raise HTTPException(status_code=401, detail="Invalid OTP")

    # Check if OTP was sent
    if mobile not in sent_otps:
        raise HTTPException(status_code=400, detail="OTP not sent or expired")

    # Generate user_id and session_token
    user_id = f"user_{mobile.replace('+', '').replace(' ', '')}"
    session_token = str(uuid.uuid4())

    # Create response (in production, create user in database)
    return VerifyOTPResponse(
        status="success",
        message="Login successful",
        user_id=user_id,
        email=f"{mobile}@kmkb.app",  # Mock email
        name=f"User {mobile[-4:]}",  # Mock name
        session_token=session_token,
        mobile_number=mobile
    )


@router.get("/health")
async def auth_health():
    """Health check for auth service"""
    return {"status": "healthy", "service": "auth"}
