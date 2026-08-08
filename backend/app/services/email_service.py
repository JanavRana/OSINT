import json
import logging
import urllib.request
import urllib.error
from app.core.config import get_settings

logger = logging.getLogger(__name__)

class EmailService:
    @staticmethod
    def _log_code(to_email: str, code: str, reason: str):
        print(f"\n{'=' * 56}\n  [{reason}] OTP for {to_email}: {code}\n{'=' * 56}\n", flush=True)
        
    @staticmethod
    def send_otp_email(to_email: str, otp: str) -> None:
        settings = get_settings()
        
        if not settings.emailjs_service_id or not settings.emailjs_public_key:
            logger.warning("EmailJS keys are missing. Simulating email send.")
            EmailService._log_code(to_email, otp, "NO MAIL TRANSPORT")
            return
            
        payload = {
            "service_id": settings.emailjs_service_id,
            "template_id": settings.emailjs_template_id,
            "user_id": settings.emailjs_public_key,
            "accessToken": settings.emailjs_private_key,
            "template_params": {
                "to_email": to_email,
                "otp": otp,
                "passcode": otp,
                "time": "15 minutes"
            }
        }
        
        req = urllib.request.Request("https://api.emailjs.com/api/v1.0/email/send", method="POST")
        req.add_header("Content-Type", "application/json")
        req.add_header("User-Agent", "IntelWeave-Backend/1.0")
        
        try:
            with urllib.request.urlopen(req, data=json.dumps(payload).encode("utf-8"), timeout=15) as response:
                result = response.read()
                logger.info("EmailJS API email sent successfully.")
        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8', errors='replace')
            logger.error(f"EmailJS API HTTP error: {e.code} - {error_body}")
            EmailService._log_code(to_email, otp, "EMAILJS REJECTED - code logged instead")
        except Exception as e:
            logger.error(f"Failed to send email to {to_email} via EmailJS: {e}")
            EmailService._log_code(to_email, otp, "DELIVERY FAILED - code logged instead")
