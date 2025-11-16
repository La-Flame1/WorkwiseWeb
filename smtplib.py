# workwiseweb/smtplib.py

import os
from typing import Optional

# Safely get environment variables
SMTP_USERNAME: Optional[str] = os.getenv('SMTP_USERNAME')
SMTP_PASSWORD: Optional[str] = os.getenv('SMTP_PASSWORD')
SMTP_SERVER: str = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
SMTP_PORT: int = int(os.getenv('SMTP_PORT', '587'))

# Optional: Validate at startup
if SMTP_USERNAME and SMTP_PASSWORD:
    print("SMTP configured for password reset emails.")
else:
    print("Warning: SMTP not configured. Password reset emails will be skipped.")

def send_email(to: str, subject: str, body: str) -> bool:
    if not SMTP_USERNAME or not SMTP_PASSWORD:
        print(f"SMTP not configured. Skipping email to {to}")
        return False

    try:
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart

        msg = MIMEMultipart()
        msg['From'] = SMTP_USERNAME
        msg['To'] = to
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()
        print(f"Email sent to {to}")
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False