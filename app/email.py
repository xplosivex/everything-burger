import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.config import SMTP_SERVER, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD, BASE_URL

logger = logging.getLogger(__name__)


def send_reset_email(email, token):
    msg = MIMEMultipart()
    msg['From'] = SMTP_USERNAME
    msg['To'] = email
    msg['Subject'] = "Everything Burger Password Reset Request"

    body = f"""
    To reset your password, click the following link:
    {BASE_URL}/reset_password/{token}

    This link will expire in 1 hour.
    """

    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT)
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        logger.error(f"Failed to send email: {str(e)}")
        return False


def send_welcome_email(email, username):
    msg = MIMEMultipart()
    msg['From'] = SMTP_USERNAME
    msg['To'] = email
    msg['Subject'] = "Welcome to Everything Burger!"

    body = f"""
    Hi {username},

    Welcome to Everything Burger! It's the burger that does everything.
    If you can dream it, we can generate it.

    We hope you enjoy your time here.
    Thanks,
    The Everything Burger Creator.
    """

    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT)
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        logger.error(f"Failed to send welcome email: {str(e)}")
        return False
