"""WhatsApp Service using Twilio for sending recipes to maid"""

from typing import Optional, Tuple
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

from annapurna.config import settings
from annapurna.models.base import SessionLocal
from annapurna.models.recipe import Recipe
from annapurna.models.user_preferences import UserProfile, OnboardingSession


class WhatsAppService:
    """Service for sending recipes via WhatsApp using Twilio"""

    def __init__(self):
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

        # WhatsApp number format: whatsapp:+1234567890
        self.whatsapp_from = f"whatsapp:{settings.twilio_whatsapp_number}" if settings.twilio_whatsapp_number else None

    def _normalize_phone(self, phone: str) -> str:
        """Normalize phone number for WhatsApp (requires country code)"""
        phone = phone.strip().replace(" ", "").replace("-", "")

        # Add India country code if not present
        if not phone.startswith("+"):
            if phone.startswith("91") and len(phone) == 12:
                phone = "+" + phone
            elif len(phone) == 10:
                phone = "+91" + phone

        return phone

    def _format_recipe_message(self, recipe: Recipe) -> str:
        """Format recipe as WhatsApp message"""
        message_parts = []

        # Title
        message_parts.append(f"*{recipe.title}*")
        message_parts.append("")

        # Time info
        if recipe.total_time_minutes:
            message_parts.append(f"⏱️ Time: {recipe.total_time_minutes} minutes")

        if recipe.servings:
            message_parts.append(f"👥 Servings: {recipe.servings}")

        message_parts.append("")

        # Ingredients
        if recipe.ingredients:
            message_parts.append("*Ingredients:*")
            for ing in recipe.ingredients[:15]:  # Limit to 15 ingredients
                name = ing.get('name', ing) if isinstance(ing, dict) else str(ing)
                quantity = ing.get('quantity', '') if isinstance(ing, dict) else ''
                unit = ing.get('unit', '') if isinstance(ing, dict) else ''
                
                ing_text = f"• {quantity} {unit} {name}".strip()
                ing_text = ' '.join(ing_text.split())  # Remove extra spaces
                message_parts.append(ing_text)

            if len(recipe.ingredients) > 15:
                message_parts.append(f"  ... and {len(recipe.ingredients) - 15} more")

            message_parts.append("")

        # Instructions
        if recipe.steps:
            message_parts.append("*Instructions:*")
            for i, step in enumerate(recipe.steps[:10], 1):  # Limit to 10 steps
                instruction = step.get('instruction', step) if isinstance(step, dict) else str(step)
                message_parts.append(f"{i}. {instruction}")

            if len(recipe.steps) > 10:
                message_parts.append(f"... and {len(recipe.steps) - 10} more steps")

        message_parts.append("")
        message_parts.append("_Sent from KMKB App_")

        return "\n".join(message_parts)

    def get_maid_phone(self, user_id: str, db=None) -> Optional[str]:
        """Get maid phone number from onboarding session data"""
        close_session = False
        if db is None:
            db = SessionLocal()
            close_session = True

        try:
            # First get the user profile
            profile = db.query(UserProfile).filter(
                UserProfile.user_id == user_id
            ).first()

            if not profile:
                return None

            # Get the onboarding session which has step_data with maid phone
            session = db.query(OnboardingSession).filter(
                OnboardingSession.user_profile_id == profile.id
            ).first()

            if session and session.step_data:
                # Maid phone could be in various steps - check all
                for step_key in ['step_5', 'step_6', 'step_7', 'step_8']:
                    step_data = session.step_data.get(step_key, {})
                    maid_phone = step_data.get('maid_phone_number')
                    if maid_phone:
                        return maid_phone

            # DEV MODE: If no maid phone found but user has profile, use test number
            if settings.environment != "production":
                return "+919999999999"

            return None
        finally:
            if close_session:
                db.close()

    def send_recipe_to_maid(
        self,
        user_id: str,
        recipe_id: str,
        db=None
    ) -> Tuple[bool, str]:
        """
        Send recipe to user's maid via WhatsApp.

        Args:
            user_id: User ID
            recipe_id: Recipe ID to send

        Returns:
            Tuple of (success, message)
        """
        close_session = False
        if db is None:
            db = SessionLocal()
            close_session = True

        try:
            # Check if WhatsApp is configured (skip in dev mode)
            if settings.environment == "production" and (not self.twilio_enabled or not self.whatsapp_from):
                return False, "WhatsApp is not configured. Please contact support."

            # Get maid phone number
            maid_phone = self.get_maid_phone(user_id, db)
            if not maid_phone:
                return False, "No maid phone number configured. Please update your profile."

            # Normalize phone number
            maid_phone = self._normalize_phone(maid_phone)
            whatsapp_to = f"whatsapp:{maid_phone}"

            # Get recipe
            recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
            if not recipe:
                return False, "Recipe not found."

            # Format message
            message_body = self._format_recipe_message(recipe)

            # Send via Twilio WhatsApp
            if settings.environment == "production":
                try:
                    # Send text message
                    message = self.twilio_client.messages.create(
                        body=message_body,
                        from_=self.whatsapp_from,
                        to=whatsapp_to
                    )

                    # Optionally send image if available
                    if recipe.primary_image_url:
                        self.twilio_client.messages.create(
                            body="",
                            from_=self.whatsapp_from,
                            to=whatsapp_to,
                            media_url=[recipe.primary_image_url]
                        )

                    return True, f"Recipe sent to maid at {maid_phone}"

                except TwilioRestException as e:
                    print(f"Twilio WhatsApp error: {e}")
                    return False, "Failed to send WhatsApp message. Please try again."
            else:
                # Development mode - just log
                print(f"[DEV] Would send WhatsApp to {whatsapp_to}:")
                print(message_body[:500] + "..." if len(message_body) > 500 else message_body)
                return True, f"[DEV] Recipe would be sent to {maid_phone}"

        finally:
            if close_session:
                db.close()


# Singleton instance
whatsapp_service = WhatsAppService()
