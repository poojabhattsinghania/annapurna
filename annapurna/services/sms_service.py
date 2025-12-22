"""SMS Service using Twilio for OTP delivery"""

import random
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Tuple
import redis
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

from annapurna.config import settings


class SMSService:
    """Service for sending OTP via Twilio SMS"""

    # OTP Configuration
    OTP_LENGTH = 6
    OTP_EXPIRY_MINUTES = 5
    MAX_OTP_ATTEMPTS = 3
    RATE_LIMIT_WINDOW_MINUTES = 10
    DEV_OTP = "123456"  # Fixed OTP for development/testing

    # Redis key prefixes
    OTP_KEY_PREFIX = "otp:"
    RATE_LIMIT_KEY_PREFIX = "otp_rate:"

    def __init__(self):
        self.redis_client = redis.from_url(settings.redis_url)

        # Initialize Twilio client only if credentials are configured
        if settings.twilio_account_sid and settings.twilio_auth_token:
            self.twilio_client = Client(
                settings.twilio_account_sid,
                settings.twilio_auth_token
            )
            self.twilio_enabled = True
        else:
            self.twilio_client = None
            self.twilio_enabled = False

    def _generate_otp(self) -> str:
        """Generate OTP - fixed in dev mode, random in production"""
        if settings.environment != "production":
            return self.DEV_OTP
        return ''.join([str(random.randint(0, 9)) for _ in range(self.OTP_LENGTH)])

    def _hash_otp(self, otp: str) -> str:
        """Hash OTP for secure storage"""
        return hashlib.sha256(otp.encode()).hexdigest()

    def _normalize_phone(self, phone: str) -> str:
        """Normalize phone number (remove spaces, ensure country code)"""
        phone = phone.strip().replace(" ", "").replace("-", "")

        # Add India country code if not present
        if not phone.startswith("+"):
            if phone.startswith("91") and len(phone) == 12:
                phone = "+" + phone
            elif len(phone) == 10:
                phone = "+91" + phone

        return phone

    def check_rate_limit(self, mobile_number: str) -> Tuple[bool, int]:
        """
        Check if user has exceeded OTP rate limit.

        Returns:
            Tuple of (is_allowed, attempts_remaining)
        """
        phone = self._normalize_phone(mobile_number)
        rate_key = f"{self.RATE_LIMIT_KEY_PREFIX}{phone}"

        attempts = self.redis_client.get(rate_key)
        if attempts is None:
            return True, self.MAX_OTP_ATTEMPTS

        attempts = int(attempts)
        if attempts >= self.MAX_OTP_ATTEMPTS:
            return False, 0

        return True, self.MAX_OTP_ATTEMPTS - attempts

    def _increment_rate_limit(self, mobile_number: str):
        """Increment OTP attempt counter"""
        phone = self._normalize_phone(mobile_number)
        rate_key = f"{self.RATE_LIMIT_KEY_PREFIX}{phone}"

        pipe = self.redis_client.pipeline()
        pipe.incr(rate_key)
        pipe.expire(rate_key, self.RATE_LIMIT_WINDOW_MINUTES * 60)
        pipe.execute()

    def send_otp(self, mobile_number: str) -> Tuple[bool, str, Optional[str]]:
        """
        Send OTP to mobile number.

        Args:
            mobile_number: Phone number to send OTP to

        Returns:
            Tuple of (success, message, otp_for_dev)
            otp_for_dev is only returned in development mode
        """
        phone = self._normalize_phone(mobile_number)

        # Check rate limit
        is_allowed, remaining = self.check_rate_limit(phone)
        if not is_allowed:
            return False, f"Too many OTP requests. Please try again in {self.RATE_LIMIT_WINDOW_MINUTES} minutes.", None

        # Generate OTP
        otp = self._generate_otp()
        otp_hash = self._hash_otp(otp)

        # Store OTP in Redis with expiry
        otp_key = f"{self.OTP_KEY_PREFIX}{phone}"
        self.redis_client.setex(
            otp_key,
            self.OTP_EXPIRY_MINUTES * 60,
            otp_hash
        )

        # Increment rate limit counter
        self._increment_rate_limit(phone)

        # Send via Twilio if enabled
        if self.twilio_enabled and settings.environment == "production":
            try:
                message = self.twilio_client.messages.create(
                    body=f"Your KMKB verification code is: {otp}. Valid for {self.OTP_EXPIRY_MINUTES} minutes.",
                    from_=settings.twilio_phone_number,
                    to=phone
                )
                return True, f"OTP sent to {phone}", None
            except TwilioRestException as e:
                # Log error but don't expose details to user
                print(f"Twilio error: {e}")
                return False, "Failed to send OTP. Please try again.", None
        else:
            # Development mode - return OTP in response
            return True, f"OTP sent to {phone}", otp

    def verify_otp(self, mobile_number: str, otp: str) -> Tuple[bool, str]:
        """
        Verify OTP for mobile number.

        Args:
            mobile_number: Phone number
            otp: OTP to verify

        Returns:
            Tuple of (success, message)
        """
        phone = self._normalize_phone(mobile_number)
        otp_key = f"{self.OTP_KEY_PREFIX}{phone}"

        # Get stored OTP hash
        stored_hash = self.redis_client.get(otp_key)
        if stored_hash is None:
            return False, "OTP expired or not sent. Please request a new OTP."

        # Verify OTP
        otp_hash = self._hash_otp(otp.strip())
        if otp_hash != stored_hash.decode('utf-8'):
            return False, "Invalid OTP. Please try again."

        # Delete OTP after successful verification
        self.redis_client.delete(otp_key)

        return True, "OTP verified successfully"

    def get_otp_ttl(self, mobile_number: str) -> int:
        """Get remaining TTL for OTP in seconds"""
        phone = self._normalize_phone(mobile_number)
        otp_key = f"{self.OTP_KEY_PREFIX}{phone}"
        ttl = self.redis_client.ttl(otp_key)
        return max(0, ttl)


# Singleton instance
sms_service = SMSService()
