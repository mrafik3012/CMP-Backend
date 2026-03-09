"""Send OTP via SMS and/or email. Replace with real SMS/email provider in production."""
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def normalize_phone(phone: str) -> str:
    """Normalize to E.164-like: digits only, optional leading +."""
    digits = "".join(c for c in phone if c.isdigit())
    if not digits:
        return phone.strip()
    if phone.strip().startswith("+"):
        return "+" + digits
    return "+" + digits if len(digits) >= 10 else digits


def send_otp_sms(phone: str, code: str) -> bool:
    """Send OTP via SMS. Override with Twilio/MSG91/etc. in production."""
    # TODO: Integrate Twilio, MSG91, or other SMS gateway
    logger.info("OTP SMS [%s]: %s", phone, code)
    print(f"[OTP SMS] To {phone}: {code}")
    return True


def send_otp_email(email: str, code: str) -> bool:
    """Send OTP via email (fallback). Override with SendGrid/Mailgun in production."""
    # TODO: Integrate email provider
    logger.info("OTP Email [%s]: %s", email, code)
    print(f"[OTP Email] To {email}: {code}")
    return True


def send_login_otp(phone: str, code: str, email: Optional[str] = None) -> bool:
    """Deliver OTP: SMS to phone first; if email given, can also send to email as backup. User lookup is by phone only (caller finds user by phone)."""
    if send_otp_sms(phone, code):
        return True
    if email:
        return send_otp_email(email, code)
    return False
