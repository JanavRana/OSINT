import json
import logging
import urllib.request
import urllib.error
from app.core.config import get_settings

logger = logging.getLogger(__name__)

class EmailService:
    @staticmethod
    def _log_code(to_email: str, code: str, reason: str):
        # Print clearly to the console so it's easy to copy during testing
        print(f"\n{'=' * 56}\n  [{reason}] OTP for {to_email}: {code}\n{'=' * 56}\n", flush=True)
        
    @staticmethod
    def send_otp_email(to_email: str, otp: str) -> None:
        settings = get_settings()
        
        # If no API key is provided, just log it and return (this prevents 500 errors!)
        if not settings.resend_api_key:
            logger.warning("RESEND_API_KEY is not set. Simulating email send.")
            EmailService._log_code(to_email, otp, "NO MAIL TRANSPORT")
            return
            
        html_content = f"""\
<html>
  <body>
    <p>Your verification code is:</p>
    <h2>{otp}</h2>
    <p>This code expires in {settings.otp_expire_minutes} minutes.</p>
  </body>
</html>
"""
        
        payload = {
            "from": settings.resend_from_email,
            "to": [to_email],
            "subject": "Verify your Intel Weave account",
            "html": html_content
        }
        
        req = urllib.request.Request("https://api.resend.com/emails", method="POST")
        req.add_header("Authorization", f"Bearer {settings.resend_api_key}")
        req.add_header("Content-Type", "application/json")
        req.add_header("User-Agent", "IntelWeave-Backend/1.0")
        
        try:
            with urllib.request.urlopen(req, data=json.dumps(payload).encode("utf-8"), timeout=10) as response:
                result = response.read()
                logger.info("Resend API email sent successfully.")
        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8', errors='replace')
            logger.error(f"Resend API HTTP error: {e.code} - {error_body}")
            # Provider rejected it (unverified domain, bad key, sandbox limit). 
            # We swallow the error and log the OTP to the console instead!
            EmailService._log_code(to_email, otp, "RESEND REJECTED - code logged instead")
        except Exception as e:
            logger.error(f"Failed to send email to {to_email} via Resend: {e}")
            # Network issue or timeout. Swallow error and log.
            EmailService._log_code(to_email, otp, "DELIVERY FAILED - code logged instead")
