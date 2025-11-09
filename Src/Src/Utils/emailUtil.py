import smtplib
import random
import string
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

# Email configuration - UPDATE THESE WITH YOUR ACTUAL EMAIL SETTINGS
SMTP_SERVER = "smtp.gmail.com"  # or your email provider's SMTP server
SMTP_PORT = 587
SENDER_EMAIL = "airventure027@gmail.com"  # Replace with your email
SENDER_PASSWORD = "AirVenture123"  # Replace with your app password or API key
APP_NAME = "WorkWise SA"

def generate_reset_code(length: int = 6) -> str:
    """Generate a random 6-digit reset code"""
    return ''.join(random.choices(string.digits, k=length))

def send_password_reset_email(recipient_email: str, reset_code: str, username: str) -> bool:
    """
    Send password reset email with verification code
    
    Args:
        recipient_email: User's email address
        reset_code: 6-digit verification code
        username: User's username
        
    Returns:
        True if email sent successfully, False otherwise
    """
    try:
        # Create message
        message = MIMEMultipart("alternative")
        message["Subject"] = f"{APP_NAME} - Password Reset Code"
        message["From"] = SENDER_EMAIL
        message["To"] = recipient_email
        
        # Create HTML email content
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .container {{
                    background-color: #f8f9fa;
                    border-radius: 10px;
                    padding: 30px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }}
                .header {{
                    text-align: center;
                    margin-bottom: 30px;
                }}
                .header h1 {{
                    color: #2A7DFF;
                    margin: 0;
                    font-size: 28px;
                }}
                .header p {{
                    color: #6D7A88;
                    margin: 5px 0 0 0;
                }}
                .content {{
                    background-color: white;
                    padding: 25px;
                    border-radius: 8px;
                    margin: 20px 0;
                }}
                .code-box {{
                    background: linear-gradient(135deg, #2A7DFF 0%, #48A6FF 100%);
                    color: white;
                    font-size: 36px;
                    font-weight: bold;
                    text-align: center;
                    padding: 20px;
                    border-radius: 8px;
                    letter-spacing: 8px;
                    margin: 25px 0;
                    box-shadow: 0 4px 15px rgba(42, 125, 255, 0.3);
                }}
                .warning {{
                    background-color: #fff3cd;
                    border-left: 4px solid #ffc107;
                    padding: 15px;
                    margin: 20px 0;
                    border-radius: 4px;
                }}
                .warning p {{
                    margin: 0;
                    color: #856404;
                }}
                .footer {{
                    text-align: center;
                    margin-top: 30px;
                    color: #6D7A88;
                    font-size: 14px;
                }}
                .footer a {{
                    color: #2A7DFF;
                    text-decoration: none;
                }}
                ul {{
                    padding-left: 20px;
                }}
                li {{
                    margin-bottom: 8px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>{APP_NAME}</h1>
                    <p>Your Path to Employment Success</p>
                </div>
                
                <div class="content">
                    <h2 style="color: #333; margin-top: 0;">Password Reset Request</h2>
                    
                    <p>Hello <strong>{username}</strong>,</p>
                    
                    <p>We received a request to reset the password for your {APP_NAME} account. Use the verification code below to complete your password reset:</p>
                    
                    <div class="code-box">
                        {reset_code}
                    </div>
                    
                    <p style="text-align: center; color: #6D7A88; font-size: 14px;">
                        This code will expire in <strong>15 minutes</strong>
                    </p>
                    
                    <div class="warning">
                        <p><strong>⚠️ Security Tips:</strong></p>
                        <ul style="margin: 10px 0 0 0;">
                            <li>Never share this code with anyone</li>
                            <li>Our team will never ask for your verification code</li>
                            <li>If you didn't request this reset, please ignore this email</li>
                        </ul>
                    </div>
                    
                    <p style="margin-top: 20px;">If you didn't request a password reset, you can safely ignore this email. Your password will remain unchanged.</p>
                </div>
                
                <div class="footer">
                    <p>Need help? Contact us at <a href="mailto:support@workwise.za">support@workwise.za</a></p>
                    <p style="margin-top: 10px;">© 2025 {APP_NAME}. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Create plain text alternative
        text_content = f"""
        {APP_NAME} - Password Reset Request
        
        Hello {username},
        
        We received a request to reset the password for your {APP_NAME} account.
        
        Your verification code is: {reset_code}
        
        This code will expire in 15 minutes.
        
        Security Tips:
        - Never share this code with anyone
        - Our team will never ask for your verification code
        - If you didn't request this reset, please ignore this email
        
        If you didn't request a password reset, you can safely ignore this email.
        
        Need help? Contact us at support@workwise.za
        
        © 2025 {APP_NAME}. All rights reserved.
        """
        
        # Attach both versions
        text_part = MIMEText(text_content, "plain")
        html_part = MIMEText(html_content, "html")
        message.attach(text_part)
        message.attach(html_part)
        
        # Send email
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, recipient_email, message.as_string())
        
        return True
        
    except Exception as e:
        print(f"Failed to send email: {str(e)}")
        return False

def send_password_changed_confirmation(recipient_email: str, username: str) -> bool:
    """
    Send confirmation email after password has been changed
    
    Args:
        recipient_email: User's email address
        username: User's username
        
    Returns:
        True if email sent successfully, False otherwise
    """
    try:
        # Create message
        message = MIMEMultipart("alternative")
        message["Subject"] = f"{APP_NAME} - Password Changed Successfully"
        message["From"] = SENDER_EMAIL
        message["To"] = recipient_email
        
        # Create HTML email content
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .container {{
                    background-color: #f8f9fa;
                    border-radius: 10px;
                    padding: 30px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }}
                .header {{
                    text-align: center;
                    margin-bottom: 30px;
                }}
                .header h1 {{
                    color: #2A7DFF;
                    margin: 0;
                    font-size: 28px;
                }}
                .content {{
                    background-color: white;
                    padding: 25px;
                    border-radius: 8px;
                    margin: 20px 0;
                }}
                .success-icon {{
                    text-align: center;
                    font-size: 60px;
                    margin: 20px 0;
                }}
                .warning {{
                    background-color: #fff3cd;
                    border-left: 4px solid #ffc107;
                    padding: 15px;
                    margin: 20px 0;
                    border-radius: 4px;
                }}
                .footer {{
                    text-align: center;
                    margin-top: 30px;
                    color: #6D7A88;
                    font-size: 14px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>{APP_NAME}</h1>
                </div>
                
                <div class="content">
                    <div class="success-icon">✅</div>
                    <h2 style="color: #333; text-align: center; margin-top: 0;">Password Changed Successfully</h2>
                    
                    <p>Hello <strong>{username}</strong>,</p>
                    
                    <p>Your password has been changed successfully. You can now log in to your {APP_NAME} account using your new password.</p>
                    
                    <div class="warning">
                        <p><strong>⚠️ Didn't change your password?</strong></p>
                        <p style="margin: 10px 0 0 0;">If you did not make this change, please contact our support team immediately at <a href="mailto:support@workwise.za">support@workwise.za</a></p>
                    </div>
                </div>
                
                <div class="footer">
                    <p>© 2025 {APP_NAME}. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Attach HTML
        html_part = MIMEText(html_content, "html")
        message.attach(html_part)
        
        # Send email
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, recipient_email, message.as_string())
        
        return True
        
    except Exception as e:
        print(f"Failed to send confirmation email: {str(e)}")
        return False
