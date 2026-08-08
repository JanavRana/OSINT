import json
import logging
import urllib.request
import urllib.error
from app.core.config import get_settings

logger = logging.getLogger(__name__)

class EmailService:
    @staticmethod
    def send_otp_email(to_email: str, otp: str) -> None:
        settings = get_settings()
        
        if not settings.resend_api_key:
            logger.warning("RESEND_API_KEY is not set. Cannot send email.")
            raise Exception("RESEND_API_KEY is missing.")
            
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
        req.add_header("User-Agent", "IntelWeave-Backend/1.0 (Integration/Resend)")
        
        try:
            with urllib.request.urlopen(req, data=json.dumps(payload).encode("utf-8"), timeout=10) as response:
                result = response.read()
                logger.info(f"Resend API email sent successfully: {result}")
        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8')
            logger.error(f"Resend API HTTP error: {e.code} - {error_body}")
            raise Exception(f"Failed to send OTP email: {error_body}") from e
        except urllib.error.URLError as e:
            logger.error(f"Failed to send email to {to_email} via Resend: {e}")
            raise Exception("Failed to send OTP email via Resend.") from e
