import os
import smtplib
from email.mime.text import MIMEText

smtp_host = os.environ.get('SMTP_HOST')
smtp_port = int(os.environ.get('SMTP_PORT', 587))
smtp_user = os.environ['SMTP_USERNAME']
smtp_pass = os.environ['SMTP_PASSWORD']
smtp_from = os.environ.get('SMTP_FROM')

# Ensure required environment variables are set so a str is passed to smtplib.SMTP and message headers
if smtp_host is None:
    raise ValueError("SMTP_HOST environment variable is not set")
if smtp_from is None:
    raise ValueError("SMTP_FROM environment variable is not set")

msg = MIMEText("Your reset code: 797300")
msg['Subject'] = 'Password Reset'
msg['From'] = smtp_from
msg['To'] = 'recipient@example.com'

with smtplib.SMTP(smtp_host, smtp_port) as server:
    server.starttls()  # Enable TLS
    server.login(smtp_user, smtp_pass)
    server.send_message(msg)