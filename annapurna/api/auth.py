"""Authentication API for mobile app"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import uuid
from typing import Optional
from datetime import datetime

from annapurna.config import settings
from annapurna.services.sms_service import sms_service

router = APIRouter(prefix="/v1/auth", tags=["Authentication"])


# Request/Response models
class SendOTPRequest(BaseModel):
    mobile_number: str


class SendOTPResponse(BaseModel):
    status: str
    message: str
    mobile_number: str
    otp_expires_in_seconds: int = 300  # 5 minutes
    dev_otp: Optional[str] = None  # Only in development mode


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


class RateLimitResponse(BaseModel):
    status: str
    message: str
    retry_after_seconds: int


@router.post("/send-otp", response_model=SendOTPResponse)
async def send_otp(request: SendOTPRequest):
    """
    Send OTP to mobile number via SMS.

    Rate limited to 3 OTPs per phone number per 10 minutes.
    OTP expires after 5 minutes.

    In development mode, the OTP is returned in the response.
    In production, OTP is sent via Twilio SMS.
    """
    mobile = request.mobile_number.strip()

    if not mobile or len(mobile) < 10:
        raise HTTPException(status_code=400, detail="Invalid mobile number")

    # Check rate limit first
    is_allowed, remaining = sms_service.check_rate_limit(mobile)
    if not is_allowed:
        raise HTTPException(
            status_code=429,
            detail={
                "message": "Too many OTP requests. Please try again later.",
                "retry_after_seconds": 600  # 10 minutes
            }
        )

    # Send OTP
    success, message, dev_otp = sms_service.send_otp(mobile)

    if not success:
        raise HTTPException(status_code=500, detail=message)

    # Get TTL for response
    ttl = sms_service.get_otp_ttl(mobile)

    response = SendOTPResponse(
        status="success",
        message=message,
        mobile_number=mobile,
        otp_expires_in_seconds=ttl
    )

    # Include OTP in response for development mode
    if dev_otp and settings.environment != "production":
        response.dev_otp = dev_otp
        response.message = f"{message}. For testing, use OTP: {dev_otp}"

    return response


@router.post("/verify-otp", response_model=VerifyOTPResponse)
async def verify_otp(request: VerifyOTPRequest):
    """
    Verify OTP and login/register user.

    Returns user info and session token on success.
    Creates a new user if mobile number doesn't exist.
    """
    mobile = request.mobile_number.strip()
    otp = request.otp.strip()

    if not mobile or len(mobile) < 10:
        raise HTTPException(status_code=400, detail="Invalid mobile number")

    if not otp or len(otp) != 6:
        raise HTTPException(status_code=400, detail="OTP must be 6 digits")

    # Verify OTP
    success, message = sms_service.verify_otp(mobile, otp)

    if not success:
        raise HTTPException(status_code=401, detail=message)

    # Normalize phone for user_id
    phone_normalized = mobile.replace("+", "").replace(" ", "").replace("-", "")
    if not phone_normalized.startswith("91") and len(phone_normalized) == 10:
        phone_normalized = "91" + phone_normalized

    # Generate user_id and session_token
    user_id = f"user_{phone_normalized}"
    session_token = str(uuid.uuid4())

    # TODO: In production, create/fetch user from database here
    # For now, return mock user data

    return VerifyOTPResponse(
        status="success",
        message="Login successful",
        user_id=user_id,
        email=f"{phone_normalized}@kmkb.app",  # Mock email
        name=f"User {mobile[-4:]}",  # Mock name
        session_token=session_token,
        mobile_number=mobile
    )


@router.get("/otp-status")
async def get_otp_status(mobile_number: str):
    """
    Check if OTP was sent and get remaining time.
    Useful for showing countdown timer in the app.
    """
    ttl = sms_service.get_otp_ttl(mobile_number)

    if ttl <= 0:
        return {
            "status": "expired",
            "message": "No active OTP. Please request a new one.",
            "remaining_seconds": 0
        }

    return {
        "status": "active",
        "message": "OTP is still valid",
        "remaining_seconds": ttl
    }


@router.get("/health")
async def auth_health():
    """Health check for auth service"""
    return {
        "status": "healthy",
        "service": "auth",
        "twilio_enabled": sms_service.twilio_enabled,
        "environment": settings.environment
    }
