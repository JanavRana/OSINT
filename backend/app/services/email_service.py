import smtplib
import logging
from email.message import EmailMessage
from app.core.config import get_settings

logger = logging.getLogger(__name__)

class EmailService:
    @staticmethod
    def send_otp_email(to_email: str, otp: str) -> None:
        settings = get_settings()
        
        msg = EmailMessage()
        msg["Subject"] = "Verify your Intel Weave account"
        msg["From"] = settings.smtp_from_email
        msg["To"] = to_email
        
        html_content = f"""\
<html>
  <body>
    <p>Your verification code is:</p>
    <h2>{otp}</h2>
    <p>This code expires in {settings.otp_expire_minutes} minutes.</p>
  </body>
</html>
"""
        msg.add_alternative(html_content, subtype="html")
        
        try:
            server = smtplib.SMTP(settings.smtp_host, settings.smtp_port)
            if settings.smtp_use_tls:
                server.starttls()
                
            if settings.smtp_username and settings.smtp_password:
                server.login(settings.smtp_username, settings.smtp_password)
                
            server.send_message(msg)
            server.quit()
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            raise Exception("Failed to send OTP email.") from e
