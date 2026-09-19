import smtplib
import os
from enum import Enum
from dotenv import load_dotenv
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from utils.logger import logger

load_dotenv()

SMTP_KEY = os.getenv("SMTP_KEY")
SMTP_LOGIN = os.getenv("SMTP_LOGIN")
SMTP_PORT = os.getenv("SMTP_PORT")
SMTP_SERVER = os.getenv("SMTP_SERVER")

_TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), "..", "templates", "email.html")

with open(_TEMPLATE_PATH, encoding="utf-8") as _f:
    _EMAIL_TEMPLATE = _f.read()


class EmailType(str, Enum):
    REGISTRATION = "registration"
    PASSWORD_RESET = "password_reset"


_EMAIL_CONFIG: dict[EmailType, dict] = {
    EmailType.REGISTRATION: {
        "subject": "Verify your TaskFlow account",
        "title": "Confirm your email",
        "subtitle": "Enter the code below to complete your registration. It's valid for a short time — don't wait too long.",
        "expire_minutes": 3,
    },
    EmailType.PASSWORD_RESET: {
        "subject": "Reset your TaskFlow password",
        "title": "Password reset request",
        "subtitle": "We received a request to reset your password. Use the code below to proceed. If you didn't ask for this, ignore this email.",
        "expire_minutes": 5,
    },
}


def _build_html(otp: int, email_type: EmailType) -> str:
    cfg = _EMAIL_CONFIG[email_type]
    return _EMAIL_TEMPLATE.format(
        title=cfg["title"],
        subtitle=cfg["subtitle"],
        otp_code=otp,
        expire_minutes=cfg["expire_minutes"],
    )


def send_email(
    otp: int,
    user_email: str,
    email_type: EmailType = EmailType.REGISTRATION,
) -> None:
    cfg = _EMAIL_CONFIG[email_type]
    msg = MIMEMultipart("alternative")
    msg["Subject"] = cfg["subject"]
    msg["From"] = SMTP_LOGIN
    msg["To"] = user_email
    msg.attach(MIMEText(f"Your one-time code: {otp}", "plain"))
    msg.attach(MIMEText(_build_html(otp, email_type), "html"))
    try:
        with smtplib.SMTP(SMTP_SERVER, int(SMTP_PORT)) as server:
            server.starttls()
            server.login(SMTP_LOGIN, SMTP_KEY)
            server.send_message(msg)
        logger.info(f"Email ({email_type}) sent to {user_email}.")
    except Exception as ex:
        logger.error(f"Failed to send email to {user_email}: {ex}.")
