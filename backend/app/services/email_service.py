"""
Email service for sending verification and notification emails.
Uses SMTP with Gmail for sending emails.
"""
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
from app.config.settings import settings

logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending emails via SMTP."""
    
    @staticmethod
    def send_verification_email(
        to_email: str,
        username: str,
        verification_token: str
    ) -> bool:
        """
        Send email verification link to user.
        
        Args:
            to_email: Recipient email address
            username: User's username
            verification_token: Verification token for the link
            
        Returns:
            True if email sent successfully, False otherwise
        """
        try:
            # Create verification URL using configured frontend URL
            verification_url = f"{settings.frontend_url}/verify-email/{verification_token}"
            
            # Create message
            message = MIMEMultipart("alternative")
            message["Subject"] = "✉️ Verify Your Email - BiasFree News"
            message["From"] = f"{settings.mail_from_name} <{settings.mail_from}>"
            message["To"] = to_email
            
            # Create HTML content
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <style>
                    * {{
                        margin: 0;
                        padding: 0;
                        box-sizing: border-box;
                    }}
                    body {{
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                        line-height: 1.6;
                        color: #333333;
                        background: #f4f7fa;
                        padding: 20px;
                    }}
                    .email-wrapper {{
                        max-width: 600px;
                        margin: 0 auto;
                        background: white;
                        border-radius: 16px;
                        overflow: hidden;
                        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
                    }}
                    .header {{
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        padding: 40px 30px;
                        text-align: center;
                    }}
                    .header h1 {{
                        color: white;
                        font-size: 28px;
                        font-weight: 700;
                        margin-bottom: 10px;
                        text-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    }}
                    .header p {{
                        color: rgba(255, 255, 255, 0.95);
                        font-size: 16px;
                        margin: 0;
                    }}
                    .content {{
                        padding: 40px 30px;
                        background: white;
                    }}
                    .greeting {{
                        font-size: 20px;
                        font-weight: 600;
                        color: #2d3748;
                        margin-bottom: 20px;
                    }}
                    .message {{
                        color: #4a5568;
                        font-size: 15px;
                        line-height: 1.8;
                        margin-bottom: 30px;
                    }}
                    .button-container {{
                        text-align: center;
                        margin: 35px 0;
                    }}
                    .verify-button {{
                        display: inline-block;
                        padding: 16px 40px;
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        color: #ffffff !important;
                        text-decoration: none;
                        border-radius: 12px;
                        font-weight: 600;
                        font-size: 16px;
                        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
                        transition: all 0.3s ease;
                        letter-spacing: 0.5px;
                    }}
                    .verify-button:hover {{
                        transform: translateY(-2px);
                        box-shadow: 0 6px 20px rgba(102, 126, 234, 0.5);
                    }}
                    .divider {{
                        height: 1px;
                        background: linear-gradient(to right, transparent, #e2e8f0, transparent);
                        margin: 30px 0;
                    }}
                    .alternative-link {{
                        background: #f7fafc;
                        border: 1px solid #e2e8f0;
                        border-radius: 8px;
                        padding: 16px;
                        margin: 25px 0;
                    }}
                    .alternative-link p {{
                        color: #718096;
                        font-size: 13px;
                        margin-bottom: 8px;
                        font-weight: 500;
                    }}
                    .link-text {{
                        color: #667eea;
                        font-size: 12px;
                        word-break: break-all;
                        font-family: 'Courier New', monospace;
                        background: white;
                        padding: 10px;
                        border-radius: 6px;
                        border: 1px solid #e2e8f0;
                    }}
                    .warning-box {{
                        background: #fff5f5;
                        border-left: 4px solid #fc8181;
                        padding: 16px;
                        border-radius: 8px;
                        margin: 25px 0;
                    }}
                    .warning-box p {{
                        color: #742a2a;
                        font-size: 14px;
                        margin: 0;
                    }}
                    .warning-box strong {{
                        color: #9b2c2c;
                    }}
                    .info-box {{
                        background: #ebf8ff;
                        border-left: 4px solid #4299e1;
                        padding: 16px;
                        border-radius: 8px;
                        margin: 20px 0;
                    }}
                    .info-box p {{
                        color: #2c5282;
                        font-size: 14px;
                        margin: 0;
                        line-height: 1.6;
                    }}
                    .footer {{
                        background: #f7fafc;
                        padding: 30px;
                        text-align: center;
                        border-top: 1px solid #e2e8f0;
                    }}
                    .footer p {{
                        color: #718096;
                        font-size: 13px;
                        margin: 8px 0;
                    }}
                    .footer-links {{
                        margin-top: 15px;
                    }}
                    .footer-links a {{
                        color: #667eea;
                        text-decoration: none;
                        margin: 0 10px;
                        font-size: 12px;
                    }}
                    .logo {{
                        font-size: 32px;
                        margin-bottom: 10px;
                    }}
                </style>
            </head>
            <body>
                <div class="email-wrapper">
                    <div class="header">
                        <div class="logo">📰</div>
                        <h1>Welcome to BiasFree News!</h1>
                        <p>Verify your email to get started</p>
                    </div>
                    
                    <div class="content">
                        <div class="greeting">Hello {username}! 👋</div>
                        
                        <div class="message">
                            Thank you for creating an account with <strong>BiasFree News</strong> - your trusted source for unbiased and accurate news analysis.
                        </div>
                        
                        <div class="message">
                            To complete your registration and start exploring unbiased news content, please verify your email address by clicking the button below:
                        </div>
                        
                        <div class="button-container">
                            <a href="{verification_url}" class="verify-button">
                                ✉️ Verify Email Address
                            </a>
                        </div>
                        
                        <div class="divider"></div>
                        
                        <div class="alternative-link">
                            <p>Or copy and paste this link in your browser:</p>
                            <div class="link-text">{verification_url}</div>
                        </div>
                        
                        <div class="warning-box">
                            <p><strong>⚠️ Important:</strong> This verification link will expire in <strong>{settings.verification_token_expiration_minutes} minute(s)</strong> for security reasons.</p>
                        </div>
                        
                        <div class="divider"></div>
                        
                        <div class="info-box">
                            <p><strong>🔒 Security Note:</strong> If you didn't create an account with BiasFree News, please ignore this email. Your email address will not be used without verification.</p>
                        </div>
                    </div>
                    
                    <div class="footer">
                        <p><strong>BiasFree News</strong></p>
                        <p>Unbiased. Accurate. Trustworthy.</p>
                        <p style="margin-top: 15px;">© 2026 BiasFree News. All rights reserved.</p>
                        <p style="font-size: 12px; color: #a0aec0; margin-top: 10px;">
                            This is an automated email. Please do not reply to this message.
                        </p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            # Create plain text version as fallback
            text_content = f"""
            Welcome to BiasFree News!
            
            Hello {username},
            
            Thank you for signing up. Please verify your email address by clicking the link below:
            
            {verification_url}
            
            This verification link will expire in 24 hours.
            
            If you didn't create an account with BiasFree News, please ignore this email.
            
            Best regards,
            BiasFree News Team
            """
            
            # Attach both HTML and plain text versions
            part1 = MIMEText(text_content, "plain")
            part2 = MIMEText(html_content, "html")
            message.attach(part1)
            message.attach(part2)
            
            # Connect to SMTP server and send email
            with smtplib.SMTP(settings.mail_server, settings.mail_port) as server:
                server.starttls()  # Secure the connection
                server.login(settings.mail_username, settings.mail_password)
                server.send_message(message)
            
            logger.info(f"Verification email sent successfully to {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send verification email to {to_email}: {str(e)}")
            return False
    
    @staticmethod
    def send_password_reset_email(
        to_email: str,
        username: str,
        reset_token: str
    ) -> bool:
        """
        Send password reset link to user.
        
        Args:
            to_email: Recipient email address
            username: User's username
            reset_token: Password reset token
            
        Returns:
            True if email sent successfully, False otherwise
        """
        try:
            reset_url = f"http://localhost:5174/reset-password/{reset_token}"
            
            message = MIMEMultipart("alternative")
            message["Subject"] = "Password Reset Request - BiasFree News"
            message["From"] = f"{settings.mail_from_name} <{settings.mail_from}>"
            message["To"] = to_email
            
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body {{
                        font-family: Arial, sans-serif;
                        line-height: 1.6;
                        color: #333;
                    }}
                    .container {{
                        max-width: 600px;
                        margin: 0 auto;
                        padding: 20px;
                    }}
                    .header {{
                        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
                        color: white;
                        padding: 30px;
                        text-align: center;
                        border-radius: 10px 10px 0 0;
                    }}
                    .content {{
                        background: #f9f9f9;
                        padding: 30px;
                        border-radius: 0 0 10px 10px;
                    }}
                    .button {{
                        display: inline-block;
                        padding: 12px 30px;
                        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
                        color: white;
                        text-decoration: none;
                        border-radius: 5px;
                        margin: 20px 0;
                        font-weight: bold;
                    }}
                    .footer {{
                        text-align: center;
                        margin-top: 20px;
                        color: #666;
                        font-size: 12px;
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>🔐 Password Reset Request</h1>
                    </div>
                    <div class="content">
                        <h2>Hello {username},</h2>
                        <p>We received a request to reset your password for your BiasFree News account.</p>
                        
                        <p>Click the button below to reset your password:</p>
                        
                        <center>
                            <a href="{reset_url}" class="button">Reset Password</a>
                        </center>
                        
                        <p><strong>Note:</strong> This link will expire in 1 hour for security reasons.</p>
                        
                        <hr style="margin: 20px 0; border: none; border-top: 1px solid #ddd;">
                        
                        <p style="font-size: 14px; color: #666;">
                            If you didn't request a password reset, please ignore this email or contact support if you have concerns.
                        </p>
                    </div>
                    <div class="footer">
                        <p>© 2026 BiasFree News. All rights reserved.</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            text_content = f"""
            Password Reset Request
            
            Hello {username},
            
            We received a request to reset your password. Click the link below to reset it:
            
            {reset_url}
            
            This link will expire in 1 hour.
            
            If you didn't request this, please ignore this email.
            
            Best regards,
            BiasFree News Team
            """
            
            part1 = MIMEText(text_content, "plain")
            part2 = MIMEText(html_content, "html")
            message.attach(part1)
            message.attach(part2)
            
            with smtplib.SMTP(settings.mail_server, settings.mail_port) as server:
                server.starttls()
                server.login(settings.mail_username, settings.mail_password)
                server.send_message(message)
            
            logger.info(f"Password reset email sent successfully to {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send password reset email to {to_email}: {str(e)}")
            return False


# Create global instance
email_service = EmailService()
